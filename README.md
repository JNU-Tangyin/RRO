# Regulating the imbalance for the container relocation problem: A deep reinforcement learning approach

The main objective of the container relocation problem (CRP) is to retrieve all containers stacked in a container terminal while minimizing the efforts of relocating containers. However, the serious imbalance in containers' duration of stay in the terminal causes highly inconsistent incoming and outgoing sequences of containers, creating a highly irregular problem space as a result. These intrinsic characteristics make it difficult and costly to relocate containers following human experiences. Stuck with tremendous state spaces, previous research on the CRP mostly limits the problem in a two-dimensional environment (e.g., single bay), under the assumption that a fixed container retrieval sequence is given. While in this paper, we address a three-dimensional (3D) CRP with consideration of the stochastic duration of stay of containers. We propose a two-stage prediction-optimization model to smooth the highly irregular state space by introducing historical data to predict the retrieval dates of containers. A deep reinforcement learning approach is developed to optimize relocation policies based on the predictions. A computational study on a real-world 3D container terminal show that, compared to empirical rules and approaches without predictions, the proposed model reduces the relocation rate of containers significantly. 

Feel free to watch video below.  Entities names are encrypted due to privacy reason:

https://github.com/JNU-Tangyin/RRO/assets/1193630/8ac41cf0-e800-43d2-acd2-a61d6320057b

## Files & Folders

- **datasets** the datasets to train and test the model. The files under `datasets/excel` is for prediction stage, and the files under `datasets/json` are for optimization stage.

- **figures**  all images drawn based on the training results under `results/`.

- **frontend** 3D storage yard front-end engine. It has been made standalone for future use.

- **predict** documents related to stacking days prediction model.

- **results** data output file after training.

- **rl** documents related to container relocation optimization model.

- **main.py**  main entry to run the program.

- **README.md** This file.

- **requirements.txt**  for installation of virtual env

## Getting started

1. Clone
   
   ```shell
   git clone https://github.com/JNU-Tangyin/RRO.git
   ```

2. Installation environment dependent software
   
   - install node16 # for front end
   
   - install python3
   
   - install virtualenv

```shell
pip3 install virtualenv venv
```

3. Install dependencies
   
   ```shell
   virtualenv venv
   pip install -r requirements.txt
   cd frontend
   npm install
   ```

4. Perpare data
- unzip `datasets/json/cache_main_data.json.zip` to local folder (153.3m)
5. Train and evaluate model, run frontend project.
   
   ```shell
   python3 main.py
   ```

Specifically, `main.py` does the following steps, which you can instead start them one by one:

```python
redis-server                  # start the global redis server
cd predict && python main.py  # start the predict stage
cd rl && python server.py     # start the 3d environment
cd rl && python env.py        # reinforcement learning stage
cd frontend && npm run dev    # start the frontend
```

## A Standalone 3D Simulation Environment for Container Relocation

Note: the 3d environment has now been made standalone as a python module!

If you want to run the pure environment without training, you can install `rro_env `from pypi [check this out on pypi.org](https://pypi.org/project/rro-env):

```shell
pip install rro-env
```

A toy example to run the environment:

```python
import gymnasium as gym
import rro_env
import random

Epochs = 10
env = gym.make('RROEnv-v0')
env.reset()

# get current operation able pile place list
print(env.docker_game.get_able_pile_list())

# action space and pile place mapping
actions = list(env.docker_game.get_action_space().keys())
for _ in range(Epochs):
    a = random.choice(actions)
    s = env.step(a)
    print(a)
```

## Citation



```

```

## Contact

If you have any questions or suggestions, feel free to contact:

- Yin Tang (ytang@jnu.edu.cn)
- Zengjian Ye(yiptsangkin@gmail.com)
- Jian Zhang (jianzhang@scut.edu.cn)

Or describe it in Issues.
