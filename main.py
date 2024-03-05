import os

os.system('redis-server &')     # start the redis server
os.system('cd predict && python main.py &') # start the predict stage
os.system('cd rl && python server.py &')    # start the 3d environment
os.system('cd rl && python env.py &')       # reinforcement learning stage
os.system('cd frontend && npm run dev &')   # start the frontend