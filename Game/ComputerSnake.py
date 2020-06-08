""" Snake game without the GUI"""

# Necessary Imports
import random
import abc
import tensorflow as tf
import numpy as np
import pickle

# Importing tf agents
from tf_agents.environments import py_environment
from tf_agents.environments import tf_environment
from tf_agents.environments import tf_py_environment
from tf_agents.environments import utils
from tf_agents.specs import array_spec
from tf_agents.environments import wrappers
from tf_agents.environments import suite_gym
from tf_agents.trajectories import time_step as ts

tf.compat.v1.enable_v2_behavior()

class Snake(py_environment.PyEnvironment):
    """A class which plays the primary portion of the snake game while
    receiving moves to play from other player classes. """

    """ Setup for the simulation which will run multiple games."""
    def __init__(self):
        self._action_spec = array_spec.BoundedArraySpec((), dtype=np.int32, minimum=0, maximum=3, name='action')
        self._observation_spec = array_spec.BoundedArraySpec((9,), dtype=np.int32, minimum=[5, 5, 0, 5, 5, 0, 0, 0, 0], maximum=[34, 34, 4, 34, 34, 1, 1, 1, 1], name='observation')
        self._state = [20, 20, 0, 25, 20, 0, 0, 0, 0]
        self.newGame()

    def action_spec(self):
        return self._action_spec

    def observation_spec(self):
        return self._observation_spec

    """ Creates a new game with the snake and fruit in the default positions. """
    def newGame(self):
        # Snake Body which only contains the head at this point
        self.snakeBody = [[20, 20]]

        # Initial Fruit Location
        self.fruit = [25, 20]

        # A dictionary which contains all possible locations that a fruit can be at.
        self.openLocations = {}
        for i in range(30):
            for j in range(30):
                self.openLocations[i + 30 * j] = [i + 5, j + 5]

        # Default direction which the snake will be moving in
        self.dir = 1

        # Set initial score to 1
        self.score = 1

        # Set the snake to be alive.
        self.dead = False

        # List of all the moves
        self.moves = []


    """ Restarts the game with the initial conditions of the snake and fruit.
    Also (reset)s the state variable to represent the current locations. """
    def _reset(self):
        # Resets the state to the initial state
        self._state = np.array([20, 20, 1, 25, 20, 0, 0, 0, 0], dtype=np.int32)

        # Makes the snake alive again
        self.dead = False

        # Writes the moves to the persistence file so we can see what the computer did later.
        self.persistence()

        # Resets the parameters of the snake to the initial parameters
        self.newGame()

        # Tells tensor flow to restart with the new state
        return ts.restart(self._state)

    """ Method which is called on when the snake is going to make a move. """
    def _step(self, action):
        # Starts a new game if the snake is 
        action = action + 1
        if self.dead:
            return self.reset()

        # Action represents the direction that the snake will move in.
        elif action >= 1 and action <= 4:
            self.setDir(action)

        # Error if an illegal move was passed in.
        else:
            raise ValueError('Direction must be between 1 and 4')

        # Reward represents the score of the snake in the current position.
        reward = 0.0
        discount = 0.0

        # Checks to see if the snake head reaches a fruit
        eaten = self.checkFruit()

        # Moves the snake based on the current direction. Head is a copy
        #(different pointer) of the array in snakeBody[0].
        head = self.snakeBody[0][:]
        # Right
        if (self.dir == 1):
            head[0] += 1
        # Left
        elif (self.dir == 2):
            head[0] -= 1
        # Down
        elif (self.dir == 3):
            head[1] -= 1
        # Up
        else:
            head[1] += 1
        
        # Adds the next move to the list of all the moves that were made.
        self.moves.append(self.dir)

        # Inserts the new head as the first item of snakeBody to represent a move.
        self.snakeBody.insert(0, head)

        # Only continues if game has not ended
        if (not self.checkLose()):
            # Removes head from openLocations to represent that that square is taken.
            key = convertToKey(head)
            self.openLocations.pop(convertToKey(head))

             # Removes last body part if fruit was not eaten
            if (not eaten):
                removed = self.snakeBody.pop()
                self.openLocations[convertToKey(removed)] = removed

            # Creates a new fruit if the fruit was eaten and increments score and reward.
            else:
                self.fruit = self.newFruit()
                self.updateScore()
                reward += 5.0

            danger_arr = self.danger()
            self._state = np.array([head[0], head[1], action - 1, self.fruit[0], self.fruit[1], danger_arr[0], danger_arr[1], danger_arr[2], danger_arr[3]], dtype=np.int32)
            return ts.transition(self._state, reward, discount=1.0)

        # If the snake has lost the game, this is ran
        else:
            self.dead = True
            reward -= 10.0
            return ts.termination(self._state, reward)

    """ Danger value based on self-collision and wall collision.
    0 for danger, 1 for no danger. Returns an array which has
    stored all those danger values."""
    def danger(self):
        head = self.snakeBody[0][:]
        neighborUp = int(convertToKey([head[0], head[1] + 1]) in self.openLocations)
        neighborDown = int(convertToKey([head[0], head[1] - 1]) in self.openLocations)
        neighborLeft = int(convertToKey([head[0] - 1, head[1]]) in self.openLocations)
        neighborRight = int(convertToKey([head[0] + 1, head[1]]) in self.openLocations)
        return np.array([neighborUp, neighborDown, neighborLeft, neighborRight], dtype=np.int32)

    """ Increments the score """
    def updateScore(self):
        self.score += 1

    """ Changes the direction that the snake moves in.
    This essentially represents players playing the game. """
    def setDir(self, dir):
        self.dir = dir

    """ Checks to see if the game is over """
    def checkLose(self):
        head = self.snakeBody[0]

        # Checks to see if the snake collides without itself or goes out of bounds
        if (head[0] < 5 or head[0] > 34 or head[1] < 5 or head[1] > 34
                or not convertToKey(head) in self.openLocations):
            self._reset()
            self.dead = True
            return True

    """ Checks to see if the snake has eaten a fruit or not """
    def checkFruit(self):
        # Returns True if the snake head is at a fruit location
        return self.snakeBody[0] == self.fruit

    """ Returns location of where the next fruit should be. """
    def newFruit(self):
        return random.choice(list(self.openLocations.values()))

    """ Sets up persistence of the stored moves."""
    def persistence(self):
        with open('Simulations/simulation1test.txt', 'wb') as sim_moves:
            pickle.dump(self.moves, sim_moves)

""" Converts a given location to a key for openLocations dictionary. 
NOT A CLASS METHOD!"""
def convertToKey(location):
    return location[0] - 5 + 30 * (location[1] - 5)
