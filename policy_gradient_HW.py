
import tensorflow as tf
import cv2
import pong_game as game
import random
import numpy as np


# Game name.
GAME = 'Pong'

# Number of valid actions.
ACTIONS = 3

# Decay rate of past observations.
GAMMA = 0.99 
# GAMMA = 0.0002 
# Timesteps to observe before training.
# OBSERVE = 500. 

# Frames over which to anneal epsilon.
# EXPLORE = 500. 
EXPLORE = 500000.
# Timesteps to observe before training.
OBSERVE = 5000. 

# Frames over which to anneal epsilon.
# EXPLORE = 5. 
# EXPLORE = 1. 

# Final value of epsilon.
FINAL_EPSILON = 0.05 
# FINAL_EPSILON = 0.9995 

# Starting value of epsilon.
INITIAL_EPSILON = 1.0 

# Size of minibatch.
BATCH = 32 

# Only select an action every Kth frame, repeat the same action for other frames.
K = 2

# Learning rate.
lr = 1e-6




def discount_rewards(r):
    discounted_r=np.zeros(np.shape(r))
    c,last_index,mean=0.0,0,0.0
    for i in range(len(r)):
        if r[i]== -1 or r[i] == 1:
            c=c+1.0
            for j in range(len(r[last_index:i+1])):
                    if j==0 :
                        discounted_r[i-j]=r[i-j]
                    else:
                        discounted_r[i-j]=r[i-j]+GAMMA*(discounted_r[i-j+1])
            for j in range(len(r[last_index:i])):
                mean=np.mean(r[j:i+1])
                discounted_r[last_index+j]=discounted_r[last_index+j]-mean
            last_index=i+1
    for i in range(len(r)):
            discounted_r[i]=discounted_r[i]
    return discounted_r



def weight_variable(shape):
    initial = tf.truncated_normal(shape, stddev = 0.01)
    return tf.Variable(initial)

def bias_variable(shape):
    initial = tf.constant(0.01, shape = shape)
    return tf.Variable(initial)

def conv2d(x, W, stride):
    return tf.nn.conv2d(x, W, strides = [1, stride, stride, 1], padding = "SAME")

def max_pool_2x2(x):
    return tf.nn.max_pool(x, ksize = [1, 2, 2, 1], strides = [1, 2, 2, 1], padding = "SAME")

def createNetwork():

    # Initialize the network weights and biases.
    W_conv1 = weight_variable([8, 8, 4, 32])
    b_conv1 = bias_variable([32])

    W_conv2 = weight_variable([4, 4, 32, 64])
    b_conv2 = bias_variable([64])

    W_conv3 = weight_variable([3, 3, 64, 64])
    b_conv3 = bias_variable([64])

    W_fc1 = weight_variable([1600, 512])
    b_fc1 = bias_variable([512])

    W_fc2 = weight_variable([512, ACTIONS])
    b_fc2 = bias_variable([ACTIONS])

    # Input layer.
    s = tf.placeholder("float", [None, 80, 80, 4])

    # Hidden layers.
    h_conv1 = tf.nn.relu(conv2d(s, W_conv1, 4) + b_conv1)
    h_pool1 = max_pool_2x2(h_conv1)
    h_conv2 = tf.nn.relu(conv2d(h_pool1, W_conv2, 2) + b_conv2)
    h_conv3 = tf.nn.relu(conv2d(h_conv2, W_conv3, 1) + b_conv3)
    h_conv3_flat = tf.reshape(h_conv3, [-1, 1600])
    h_fc1 = tf.nn.relu(tf.matmul(h_conv3_flat, W_fc1) + b_fc1)

    # Output layer
    readout = tf.nn.softmax(tf.matmul(h_fc1, W_fc2) + b_fc2)

    return s, readout


def compute_cost(readout,action_holder,reward_holder):
    target_y=tf.reduce_sum(readout*action_holder,axis=1)
    loss=-(tf.reduce_sum((tf.log(target_y)*(reward_holder))))
    return loss



class agent():
   
    def __init__(self, s, readout):
        # Current state of the agent.
        self.state_in = s

        # Output Layer of the network.
        self.readout = readout

        # Chosen action with the maximum reward
        self.chosen_action = tf.argmax(readout, 1)

        # Placeholders for the reward.
        self.reward_holder = tf.placeholder(shape=[None], dtype=tf.float32)

        # Placeholders for the action.
        self.action_holder = tf.placeholder(shape=[None, 3], dtype=tf.int32)
        
        # Compute the Loss.
        action_holder = tf.cast(self.action_holder,dtype=tf.float32)

        # compute the loss
        self.loss = compute_cost(readout,action_holder,self.reward_holder)

        # Prepare a placeholder for the gradients.
        tvars = tf.trainable_variables()
        self.gradient_holders = []

        for idx,var in enumerate(tvars):
            placeholder = tf.placeholder(tf.float32, name=str(idx) + '_holder')
            self.gradient_holders.append(placeholder)

        # Obtain the gradients.
        self.gradients = tf.gradients(self.loss, tvars)

        # Optimizer.
        optimizer = tf.train.AdamOptimizer(learning_rate = lr)

        # Perform one update step.
        self.update_batch = optimizer.apply_gradients(zip(self.gradient_holders, tvars))


def get_action_index(readout_t,epsilon,t):
	rand_num = np.random.random()
	if OBSERVE >t or epsilon > rand_num:
		action_index = random.randint(0,2)
	else:
		action_index = np.argmax(readout_t)
	return action_index



def scale_down_epsilon(epsilon,t):
    if epsilon > FINAL_EPSILON :
        if t > OBSERVE:
            epsilon -= (INITIAL_EPSILON - FINAL_EPSILON) / EXPLORE
    return epsilon


def run_selected_action(a_t,s_t,game_state):
    x,r_t,terminal=game_state.frame_step(a_t)
    x_t = cv2.cvtColor(cv2.resize(x, (80, 80)), cv2.COLOR_BGR2GRAY)
    s_t1=np.stack((s_t[:,:,1], s_t[:,:,2], s_t[:,:,3], x_t), axis = 2)
    return s_t1,r_t,terminal 

def trainNetwork(myAgent,sess):

    # Open up a game state to communicate with emulator.
    game_state = game.GameState()


    # Initialize the sate of the game.
    do_nothing = np.zeros(ACTIONS)
    do_nothing[0] = 1
    x_t, r_0, terminal = game_state.frame_step(do_nothing)
    x_t = cv2.cvtColor(cv2.resize(x_t, (80, 80)), cv2.COLOR_BGR2GRAY)
    ret, x_t = cv2.threshold(x_t, 1, 255, cv2.THRESH_BINARY)
    s_t = np.stack((x_t, x_t, x_t, x_t), axis = 2)

    # Initialize the episose history.
    ep_history = []

    # Initialize a saver.
    saver = tf.train.Saver()

    # Initialize all variables.
    sess.run(tf.initialize_all_variables())

    # Restore the checkpoints.
    checkpoint = tf.train.get_checkpoint_state("saved_networks_policy_gradient")
    if checkpoint and checkpoint.model_checkpoint_path:
        saver.restore(sess, checkpoint.model_checkpoint_path)
        print("Successfully loaded:", checkpoint.model_checkpoint_path)
    else:
        print("Could not find old network weights")

    # Initialize the grad_buffer.
    gradBuffer = sess.run(tf.trainable_variables())
    for ix,grad in enumerate(gradBuffer):
        gradBuffer[ix] = grad * 0
        

    # Initialize the epsilon value for the exploration phase.
    epsilon = INITIAL_EPSILON

    # Initialize the iteration counter.
    t = 0      

    # For all episodes.
    while True: 

        # Choose an action epsilon-greedily.
        readout_t = myAgent.readout.eval(feed_dict = {myAgent.state_in : [s_t]})[0]
        action_index = get_action_index(readout_t,epsilon,t)
        a_t = np.zeros([ACTIONS])
        a_t[action_index] = 1

        # Scale down epsilon during the exploitation phase.
        epsilon = scale_down_epsilon(epsilon,t)


        for i in range(0, K):
            # Run the selected action and observe next state and reward.
            s_t1,r_t,terminal = run_selected_action(a_t,s_t,game_state)

            # Store the transition in the replay memory.
            ep_history.append([s_t, a_t, r_t, s_t1])

            if (terminal):
                break
            
        
        # If the episode is over
        if (terminal):

            s_j = [d[0] for d in ep_history]
            a_j = [d[1] for d in ep_history]
            r_j = [d[2] for d in ep_history]
            s_j1 = [d[3] for d in ep_history]
            score=0
            score_opponent = 0
            for i in r_j:
                if (i==1):
                    score=score+1
                if i == -1:
                    score_opponent += 1

            print("score is ", score, score_opponent)
            # Compute the discounted reward
            r_j = discount_rewards(r_j)

            s_j = np.reshape(np.vstack(s_j), [-1, 80, 80, 4])

            feed_dict={myAgent.reward_holder:r_j, myAgent.action_holder: a_j, myAgent.state_in: s_j}

            grads = sess.run(myAgent.gradients, feed_dict = feed_dict)
 
            
            
            for idx,grad in enumerate(grads):
                gradBuffer[idx] += grad



            feed_dict= dictionary = dict(zip(myAgent.gradient_holders, gradBuffer))
            _ = sess.run(myAgent.update_batch, feed_dict = feed_dict)

            # Clean the grad buffer
            for ix,grad in enumerate(gradBuffer):
                gradBuffer[ix] = grad * 0

            ep_history = []


        # Update the state.
        s_t = s_t1

        # Update the number of iterations.
        t += 1

        # Save a checkpoint every 10000 iterations.
        if t % 10000 == 0:
            saver.save(sess, 'saved_networks_policy_gradient/' + GAME + '-dqn', global_step = t)

        # Print info.
        if t % 1000 == 0:
            print("TIMESTEP", t, "/ EPSILON", epsilon, "/ ACTION", action_index, "/ REWARD", r_t, "/ Q_MAX %e" % np.max(readout_t))





def playGame():
    """Paly the pong game"""

    # Start an active session.
    sess = tf.InteractiveSession()

    # Create the network.
    s, readout = createNetwork()

    # Create an agent 
    myAgent = agent(s, readout)     

    # Train the Network.
    s, readout = trainNetwork(myAgent, sess)
    


def main():
    """ Main function """
    playGame()

if __name__ == "__main__":
    main()


