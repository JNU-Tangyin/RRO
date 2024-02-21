# Regulating the imbalance for the container relocation problem: A deep reinforcement learning approach

The main objective of the container relocation problem (CRP) is to retrieve all containers stacked in a container terminal while minimizing the efforts of relocating containers. However, the serious imbalance in containers' duration of stay in the terminal causes highly inconsistent incoming and outgoing sequences of containers, creating a highly irregular problem space as a result. These intrinsic characteristics make it difficult and costly to relocate containers following human experiences. Stuck with tremendous state spaces, previous research on the CRP mostly limits the problem in a two-dimensional environment (e.g., single bay), under the assumption that a fixed container retrieval sequence is given. While in this paper, we address a three-dimensional (3D) CRP with consideration of the stochastic duration of stay of containers. We propose a two-stage prediction-optimization model to smooth the highly irregular state space by introducing historical data to predict the retrieval dates of containers. A deep reinforcement learning approach is developed to optimize relocation policies based on the predictions. A computational study on a real-world 3D container terminal show that, compared to empirical rules and approaches without predictions, the proposed model reduces the relocation rate of containers significantly. 

codes to be released soon. Feel free to watch video below:


<iframe height=498 width=510 src="https://github.com/JNU-Tangyin/RRO/edit/main/demo.mp4">
