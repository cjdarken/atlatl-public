IMPORT_NEURAL = True

import ai.passive
import ai.random_actor
import ai.shootback
import ai.potential_field
import ai.dijkstra_demo
import ai.mcts
import ai.gym_ai_surrogate
import ai.multigym_ai
import ai.pass_agg
import ai.pass_agg_fp
import ai.pass_agg_fog
import ai.burt_reynolds_lab2
import ai.burtplus
import ai.simpleDisengage
import ai.stomp
import ai.hierarchy_template
import ai.hierarchy
import ai.setup_demo
import ai.simon_says
import ai.simpleAssault
import ai.simpleDisengage
import ai.simpleEncircle
import ai.simpleFireCoordination
import ai.simpleMovement
import ai.pass_agg_scoring
import ai.stomp_scoring
if IMPORT_NEURAL:
    import ai.neural
    import ai.azero
    import ai.dl_alpha_beta
    import ai.state_eval_gpu

ai_registry = {
              "passive" : (ai.passive.AI, {}),
              "random" : (ai.random_actor.AI, {}),
              "shootback" : (ai.shootback.AI, {}),
              "field" : (ai.potential_field.AI, {}),
              "pass-agg" : (ai.pass_agg.AI, {}),
              "pass-agg-fp" : (ai.pass_agg_fp.PassAggFpAI, {}),
              "pass-agg-fog" : (ai.pass_agg_fog.AI, {}),
              "dijkstra" : (ai.dijkstra_demo.AI, {}),

              "pass-agg-pseudo-q" : (ai.pass_agg_scoring.AI, {"score_is_Q":True, "search":"fixed"}),
              "pass-agg-state" : (ai.pass_agg_scoring.AI, {"score_is_Q":False, "search":"fixed"}),
              "stomp-scoring" : (ai.stomp_scoring.AI, {"search":"fixed"}),

              "simon-says" : (ai.simon_says.AI, {}),
              "simple-assault" : (ai.simpleAssault.AI, {}),
              "simple-disengage" : (ai.simpleDisengage.AI, {}),
              "simple-encircle" : (ai.simpleEncircle.AI, {}),
              "simple-fire-coordination" : (ai.simpleFireCoordination.AI, {}),
              "simple-movement" : (ai.simpleMovement.AI, {}),

              "mcts1k" : (ai.mcts.AI, {"max_rollouts":1000, "debug":False}),
              "mcts10k" : (ai.mcts.AI, {"max_rollouts":10000, "debug":False}),
              "mctsd" : (ai.mcts.AI, {"max_rollouts":10000, "debug":True}),

              "gym" : (ai.gym_ai_surrogate.AI, {}),
              "gymx2" : (ai.gym_ai_surrogate.AIx2, {}),
              "gym12" : (ai.gym_ai_surrogate.AITwelve, {}),
              "gym13" : (ai.gym_ai_surrogate.AI13, {}),
              "gym14" : (ai.gym_ai_surrogate.AI14, {}),
              "gym16" : (ai.gym_ai_surrogate.AI16, {}),
              "gym18" : (ai.gym_ai_surrogate.AI18, {}),
              "multigym": (ai.multigym_ai.AI, {"mode":"training"}),
              "multi-ai-rl": (ai.multigym_ai.AI, {"mode":"production", "dqn":True}),
              "multi-ai-rl-ppo": (ai.multigym_ai.AI, {"mode":"production", "dqn":False}),
              "burt-reynolds-lab2" : (ai.burt_reynolds_lab2.AI, {}),
              "burtplus" : (ai.burtplus.AI, {}),
              "stomp" : (ai.stomp.AI, {}),
              "stomp-pp" : (ai.stomp.AI, {"partialPly":True}),
              "pass" : (ai.pass_agg.AI, {"mode":"pass"}),
              "agg" : (ai.pass_agg.AI, {"mode":"agg"}),
              "hierarchy-template" : (ai.hierarchy_template.AI, {}),
              "hierarchy-random-commander" : (ai.hierarchy_template.AI, {"mode":"random_commander"}),
              "hierarchy-ignore-commander" : (ai.hierarchy_template.AI, {"mode":"ignore_commander"}),
              "deep-hierarchy" : (ai.hierarchy.AI, {}),

              "setup-demo" : (ai.setup_demo.AI, {}),
             }
             
if IMPORT_NEURAL:
    ai_registry["neural"] = (ai.neural.AI, {"doubledCoordinates":False})
    ai_registry["cnn"] = (ai.neural.AI, {"doubledCoordinates":True})
    ai_registry["hex12"] = (ai.neural.AITwelve, {"doubledCoordinates":False})
    ai_registry["hex13"] = (ai.neural.AI13, {"doubledCoordinates":False})
    ai_registry["hex14"] = (ai.neural.AI14, {"doubledCoordinates":False})
    ai_registry["hex14dqn"] = (ai.neural.AI14, {"dqn":True, "doubledCoordinates":False})
    ai_registry["hex18dqn"] = (ai.neural.AI18, {"dqn":True, "doubledCoordinates":False})
    ai_registry["mando-fun-lab3"] = (ai.neural.AI14, {"neuralNet":"ai/mandofun_c0.zip", "dqn":True, "doubledCoordinates":False})
    ai_registry["alphazero"] = (ai.azero.AIaz, {"neuralNet":"temp"})
    ai_registry["dlalphabeta"] = (ai.dl_alpha_beta.AI, {"debug":False})
    ai_registry["state-eval-gpu"] = (ai.state_eval_gpu.StateEvalGPUAI, {"partialPly":False})
    ai_registry["state-eval-gpu-pp"] = (ai.state_eval_gpu.StateEvalGPUAI, {"partialPly":True})
    ai_registry["pascal"] = (ai.dl_alpha_beta.AI, {"debug":False, "neuralNet":"ai/pass-v-pass-g3", "depthLimit": "1"})