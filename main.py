import os

os.system('redis-server &')
os.system('cd predict && python main.py &')
os.system('cd rl && python server.py &')
os.system('cd rl && python env.py &')
os.system('cd frontend && npm run dev &')