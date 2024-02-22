# Regulating the imbalance for the container relocation problem: A deep reinforcement learning approach

The main objective of the container relocation problem (CRP) is to retrieve all containers stacked in a container terminal while minimizing the efforts of relocating containers. However, the serious imbalance in containers' duration of stay in the terminal causes highly inconsistent incoming and outgoing sequences of containers, creating a highly irregular problem space as a result. These intrinsic characteristics make it difficult and costly to relocate containers following human experiences. Stuck with tremendous state spaces, previous research on the CRP mostly limits the problem in a two-dimensional environment (e.g., single bay), under the assumption that a fixed container retrieval sequence is given. While in this paper, we address a three-dimensional (3D) CRP with consideration of the stochastic duration of stay of containers. We propose a two-stage prediction-optimization model to smooth the highly irregular state space by introducing historical data to predict the retrieval dates of containers. A deep reinforcement learning approach is developed to optimize relocation policies based on the predictions. A computational study on a real-world 3D container terminal show that, compared to empirical rules and approaches without predictions, the proposed model reduces the relocation rate of containers significantly. 

codes to be released soon. 

Feel free to watch video below:

https://github.com/JNU-Tangyin/RRO/assets/1193630/17ef965e-7bac-4fde-bd6b-8723c4c7d278

## Installation Instruction
1. download
```shell
git clone https://github.com/JNU-Tangyin/RRO.git
```

## Citation

If you find this repo useful, please cite our paper.

```
@inproceedings{tang2024rro,
  title={Regulating the imbalance for the container relocation problem: A deep reinforcement
learning approach},
  author={Yin Tang
, Zengjian Ye
, Yongjian Chen
, Wanting Gao
, Zezheng Li
, Yan Li
, Yixuan Xiao
, Jie Lu
, Shuqiang Huang
, Jian Zhang∗},
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
```
2. cd into the directory, and run
```shell
python3 main.py
```
3. check the folder for ploting results and latex tables
