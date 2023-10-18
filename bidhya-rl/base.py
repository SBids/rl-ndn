
import os
import time
from sys import argv, exit
import string
import json
import errno

import numpy as np
from agent import Agent
import environment as e
from environment import _Embedding, MulticastEnvironment
import tensorflow as tf
from pathlib import Path as p


fifo_suppression_value = 'fifo_suppression_value' #we don't care if this file is chaged because we write to this file
fifo_object_details = 'fifo_object_details'
num = 0

'''
The Memory class is used to store the observations, actions, and rewards of the agent at each step during training. 
It has a store() method which takes as input the current state, the action taken by the agent, and the reward obtained, 
and stores these values in separate lists self.states, self.actions, and self.rewards, respectively.

The clear() method is used to clear the Memory object, which is useful when we want to start a new episode of training
'''

experience_dict = {}
done = 0


def generate_positional_one_hot_vector(text):
  alphabet = string.ascii_lowercase  # Get all lowercase alphabets
  digits = string.digits  # Get all digits
  symbols = "!@#$%^&*()_-+={}[]|\:;'<>?,./\""
  vocab = alphabet + digits + symbols
    
  # Create a dictionary to map characters in the vocabulary to unique indices
  char_to_index = {char: idx for idx, char in enumerate(vocab)}
    
  # Create the one-hot vector with positional encoding
  one_hot_vector = []
  for idx, char in enumerate(text.lower()):
    if char in char_to_index:
      # Get the index of the character in the vocabulary
      char_idx = char_to_index[char]
            
    # Append the character index and the position index to the one-hot vector
      one_hot_vector.append(char_idx)
      one_hot_vector.append(idx)
    
  return one_hot_vector
    

# INCOMPLETE
if __name__ == "__main__":
  # mcast_sup = MulticastSuppression(fifo_object_details, fifo_suppression_value)
  print ("The reinforcement is starting........")
  print("*********", p.cwd(), "*************") # for debugging
  

  try:
    os.mkfifo(fifo_object_details, mode=0o777)
  except OSError as oe:
    if oe.errno != errno.EEXIST:
      print("File does not exist!!!")
      raise

  counter = 0 # this is only for testing, modify accordingly
  while True:
    try:
      read_pipe = os.open(fifo_object_details, os.O_RDONLY)
      bytes = os.read(read_pipe, 1024)
      if len(bytes) == 0:
        print("length of byte is zero")
        break
      states_string = bytes.decode()
      states_dict = json.loads(states_string)
      # 1 
      # 2
      # {"expMovingAverageCurrent":"1","expMovingAveragePrev":"0","prefix_name":"\/producer\/sta1\/transfer\/v=1692376379134","dc":"1.3","wasForwarded":"true"}
      # {1/0/\/producer\/sta1\/transfer\/v=1692376379134/1.3/true} 1
      # {1/0.02/\/producer\/sta1\/transfer\/v=1692376379134/1.4/true} 2
      # 2 ={"expMovingAverageCurrent":"1","expMovingAveragePrev":"0.02","prefix_name":"\/producer\/sta1\/transfer\/v=1692376379134","dc":"1.4","wasForwarded":"true"}
      # 3 ={"expMovingAverageCurrent":"1","expMovingAveragePrev":"0.02","prefix_name":"\/producer\/sta1\/transfer\/v=1692376379134","dc":"1.2","wasForwarded":"true"}

      states_values = [str(value) for value in states_dict.values()]
      
      result = '/'.join(states_values)
      print("Fifo content : ", result)
      embeddings = generate_positional_one_hot_vector(result)    
      new_embeddings = tf.convert_to_tensor([embeddings], dtype=tf.float32)
      padding_size = 130 - new_embeddings.shape[1]
      paddings = tf.constant([[0, 0], [0, padding_size]])

      # # Pad the tensor
      padded_tensor = tf.pad(new_embeddings, paddings, 'CONSTANT')
      #padded_tensor = new_embeddings

      # Now, padded_tensor will have a shape of (1, 120)

      
      agent = Agent()
      action = agent.choose_action(padded_tensor)
      print("Final action  = ", action)
      os.close(read_pipe)

      write_pipe = os.open(fifo_object_details, os.O_WRONLY)
    
      response = "{}".format(action)
      os.write(write_pipe, response.encode())
      os.close(write_pipe)

      if states_dict["prefix_name"] in experience_dict.keys():
        dc = states_dict["ewma_dc"]
        rtt = float(states_dict["rtt"])
        srtt = float(states_dict["srtt"])
        reward = agent.get_reward(dc, rtt, srtt)
        previous_state = experience_dict[states_dict["prefix_name"]] 
        current_state = padded_tensor
        if(states_dict["ewma_dc"]=="0.0"):
          done = 1
        print("Reward", reward)
      
        
        agent.learn(previous_state, reward, current_state,done)
      experience_dict[states_dict["prefix_name"]] = embeddings
      counter = counter + 1
      print("Counter in RL: ", counter)



    except Exception as e:
      print ("exception: ", e)
  