import gym_interface
import random

#random.seed(12345)

gym_env = gym_interface.GymEnvironment("blue", "passive", scenario="atomic-city.scn", verbose=False)
obs = gym_env.reset()
print("initial observation")
print(obs)
last_true_i = 0
net_reward = 0
for i in range(12):
    action_choice = random.randint(0,6)
    action_choice = 0
    print(f"gym_main: taking action {action_choice}")
    (obs, reward, done, info) = gym_env.step(action_choice)
    print(f'reward {reward} done {done} obs below')
    print(obs)
    net_reward += reward
    #print(f"episode action count {i-last_true_i}")
    if done:
        delta = i - last_true_i
        print(f"action num {i} net_reward {net_reward} done {done} delta actions {delta} score {info['score']}")
        last_true_i = i
        net_reward = 0
    if done:
        obs = gym_env.reset()
        print("obs after reset")
        print(obs)
print("gym_main: end of code")
