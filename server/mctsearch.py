import game as gm
import math
import random
import json
import psutil

def uct_search(game, merit_const=1.5, max_rollouts=100, init_state=None, debug=False):
    class Node:
        def __init__(self, action, state, parent=None):
            self.state = state
            self.count = 0
            self.total_score = 0
            self.action = action  # Action to get to this state from parent
            self.untried_actions = game.legal_actions(state)
            random.shuffle(self.untried_actions)
            self.children = []
            self.parent = parent
            if parent:
                parent.children.append(self)
        def fully_expanded(self):
            return len(self.untried_actions)==0

    def default_policy(state):
        while not game.is_terminal(state):
            action = random.choice( game.legal_actions(state) )
            state = game.transition(state, action)
        return game.score(state)
    def tree_policy(node):
        while not game.is_terminal(node.state):
            if not node.fully_expanded():
                return expand(node)
            else:
                node = best_child(node)
        return node
    def expand(node):
        action = node.untried_actions.pop()
        state = game.transition(node.state, action)
        return Node(action,state,node)
    def best_child(node,const=merit_const):
        return max(node.children, key=lambda n:merit(n,const))
    def merit(node, const):
        mean_score = node.total_score / node.count
        return mean_score + const * math.sqrt( math.log(node.parent.count)/node.count )
    def best_action_seq(node):
        seq = []
        curr_node = node
        while curr_node:
            if not curr_node.children:
                return seq
            curr_node = max(curr_node.children, key=lambda n:merit(n,0))
            seq.append( curr_node.action )
    def run_finished():
        if max_rollouts:
            if psutil.virtual_memory().percent >= 99:
                print("Memory use exceeds 99%, ending early")
                return True
            return root.count >= max_rollouts
        return psutil.virtual_memory().percent >= 99
    def backup(node, score):
        while node != None:
            node.count += 1
            # We only need the count at the root to be correct
            if node==root or game.on_move(node.parent.state)==game.max_player():
                node.total_score += score
            else:
                node.total_score -= score
            node = node.parent
    def interactive_tree_browser():
        print("Interactive Tree Browser")
        node = root
        while True:
            print(node.state)
            print("0 Root")
            print("1 Parent")
            count = 2
            for child in node.children:
                print(f'{count} {child.action} {child.count} {child.total_score/child.count}')
                count += 1
            choice = int( input("Choice? ") )
            if choice<0:
                return
            elif choice==0:
                node = root
            elif choice==1:
                node = node.parent
            else:
                node = node.children[choice-2]
    def traverse_tree(node, depth, fn, data):
        fn(node, depth, data)
        for child in node.children:
            traverse_tree(child, depth+1, fn, data)
    def tree_stats():
        class TreeData:
            def __init__(self):
                self.num_nodes = 0
                self.max_depth = 0
                self.depth_histogram = {}
        def fn(node, depth, data):
            data.num_nodes += 1
            data.max_depth = max(depth, data.max_depth)
            data.depth_histogram[str(depth)] = data.depth_histogram.get(str(depth), 0) + 1
        data = TreeData()
        traverse_tree(root, 0, fn, data)
        print(f"Tree Stats, num_nodes {data.num_nodes} max_depth {data.max_depth}")
        for i in range(data.max_depth+1):
            print(f'{i} {data.depth_histogram[str(i)]}')

    if init_state is None:
        init_state = game.initial_state()
    root = Node( None, init_state, None )
    while not run_finished():
        node = tree_policy(root)
        rollout_max_score = default_policy(node.state)
        backup(node, rollout_max_score)

    if debug:
        print('Best Action Path')
        seq = best_action_seq(root)
        print(seq)
        
        print("Child Scores")
        for child in root.children:
            print(f'child action {child.action} count {child.count} expected score {child.total_score/child.count}')
        
        tree_stats()
        interactive_tree_browser()
    
    return best_action_seq(root)


if __name__ == "__main__":
    game_max_score = 580
    game_min_score = -680
    constant = (game_max_score-game_min_score)/math.sqrt(2)
    scenario = "column-5x5-water-flipped.scn"
    #scenario = "column2x3.scn"
    # scenario = "atomic-city.scn"
    scenarioPo = json.load( open("scenarios/"+scenario) )
    game = gm.Game(scenarioPo)
    best_moves = uct_search( game, constant, max_rollouts=10000 )
    print(f'best_moves {best_moves}')