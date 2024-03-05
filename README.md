# Regulating the imbalance for the container relocation problem: A deep reinforcement learning approach

The main objective of the container relocation problem (CRP) is to retrieve all containers stacked in a container terminal while minimizing the efforts of relocating containers. However, the serious imbalance in containers' duration of stay in the terminal causes highly inconsistent incoming and outgoing sequences of containers, creating a highly irregular problem space as a result. These intrinsic characteristics make it difficult and costly to relocate containers following human experiences. Stuck with tremendous state spaces, previous research on the CRP mostly limits the problem in a two-dimensional environment (e.g., single bay), under the assumption that a fixed container retrieval sequence is given. While in this paper, we address a three-dimensional (3D) CRP with consideration of the stochastic duration of stay of containers. We propose a two-stage prediction-optimization model to smooth the highly irregular state space by introducing historical data to predict the retrieval dates of containers. A deep reinforcement learning approach is developed to optimize relocation policies based on the predictions. A computational study on a real-world 3D container terminal show that, compared to empirical rules and approaches without predictions, the proposed model reduces the relocation rate of containers significantly. 


Feel free to watch video below.  Entities names are encrypted due to privacy reason:


https://github.com/JNU-Tangyin/RRO/assets/1193630/8ac41cf0-e800-43d2-acd2-a61d6320057b





## Files & Folders

- **datasets** the datasets to train and test. the files in datasets/excel is for prediction stage, the files in datasets/json and datasets/redis is for optimization stage.

- **figures** all images drawn based on the data from the training results.

- **frontend** 3D storage yard front-end engineering project.

- **predict** documents related to stacking days prediction model.

- **results** data output file after training.

- **rl** documents related to container relocation optimization model.

- **main.py** entry file for run program.

- **README.md** introduce how to run this project.

- **requirements.txt** for installation of virtual env


## Getting started
1. Clone
```shell
git clone https://github.com/JNU-Tangyin/RRO.git
```

2. Installation environment dependent software
- install redis-server 7.0
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

4. Prepare data
- copy datasets/redis/dump.rdb to redis-server folder
```shell
redis-server
```

5. Train and evaluate model, run frontend project.
```shell
python3 main.py
```

## Citation

If you find this repo useful, please cite our paper.

```
@inproceedings{tang2024rro,
  title={Regulating the imbalance for the container relocation problem: A deep reinforcement
learning approach},
  author={Yin Tang, Zengjian Ye, Yongjian Chen, Wanting Gao, Zezheng Li, Yan Li, Yixuan Xiao, Jie Lu, Shuqiang Huang, Jian Zhang∗},
  journal={Computers & Industrial Engineering},
  year={2024},
}
```

## Contact

If you have any questions or suggestions, feel free to contact:

- Yin Tang (ytang@jnu.edu.cn)
- Zengjian Ye()
- Jian Zhang (jianzhang@scut.edu.cn)

Or describe it in Issues.
