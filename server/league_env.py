import random

class LeagueEnvironment:
    def __init__(self, envs, probs):
        # All envs must be proper gym environments with the same spaces, metadata, and reward range
        # At each reset, one of the envs is randomly sampled using probs
        self.envs = envs
        self.probs = probs
        self.action_space = envs[0].action_space
        self.observation_space = envs[0].observation_space
        self.metadata = envs[0].metadata
        self.reward_range = envs[0].reward_range
    def reset(self):
        self.env = random.choices(self.envs,self.probs)[0]
        return self.env.reset()
    def close(self):
        pass
    def render(self):
        pass
    def step(self, action):
        return self.env.step(action)
