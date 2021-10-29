"""gcn.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/19CHiNNkww39vm_KI_Ov0GMJekRuEg3BF
"""

import numpy as np
import scipy.sparse as sp
import torch
from sklearn.preprocessing import LabelBinarizer
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.nn.init as init
import torch.optim as optim
import matplotlib.pyplot as plt

"""
normalize the data to 1.
"""
def normalize_adj(adjacency):
    adjacency += sp.eye(adjacency.shape[0])
    degree = np.array(adjacency.sum(1))
    d_hat = sp.diags(np.power(degree, -0.5).flatten())
    return d_hat.dot(adjacency).dot(d_hat).tocoo()


def normalize_features(features):
    return features / features.sum(1)

"""
load data from facebook.npz and set adjacency/features/labels
"""
def load_data():
    dataset = np.load('/content/drive/My Drive/Dataset/facebook.npz')
    edges = dataset['edges']
    features = dataset['features']
    target = dataset['target']

    # set adjacency
    n = len(target)
    x = np.zeros((n, n), dtype=np.float32)
    for i in edges:
        x[i[0]][i[1]] = 1

    edges = sp.csr_matrix(x)
    adjacency = normalize_adj(edges)

    # set features
    features = sp.csr_matrix(features, dtype=np.float32)
    features = normalize_features(features)
    features = torch.FloatTensor(np.array(features))

    # set labels
    encode_onehot = LabelBinarizer()
    labels = encode_onehot.fit_transform(target)
    labels = torch.LongTensor(np.where(labels)[1])

    num_nodes = features.shape[0]
    train_mask = np.zeros(num_nodes, dtype=np.bool)
    val_mask = np.zeros(num_nodes, dtype=np.bool)
    test_mask = np.zeros(num_nodes, dtype=np.bool)

    train_mask[0:140] = True
    val_mask[200:500] = True
    test_mask[500:1500] = True

    return adjacency, features, labels, train_mask, val_mask, test_mask

"""
Graph Convalution
"""
class GraphConvolution(nn.Module):
    def __init__(self, input_dim, output_dim, use_bias=True):
		"""
		input_dim: int. Dimension of input nodes
		output_dim: int. Dimension of output nodes
		use_bias : bool, optional.
		"""
        super(GraphConvolution, self).__init__()
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.use_bias = use_bias
        self.weight = nn.Parameter(torch.Tensor(input_dim, output_dim))
        if self.use_bias:
            self.bias = nn.Parameter(torch.Tensor(output_dim))
        else:
            self.register_parameter('bias', None)
        self.reset_parameters()

    def reset_parameters(self):
        init.kaiming_uniform_(self.weight)
        if self.use_bias:
            init.zeros_(self.bias)

    def forward(self, adjacency, input_feature):
		"""
		adjacency matrix is sparse matrix, thus this will use sparse when
		calculate.
		adjacency: torch.sparse.FloatTensor
		input_feature: torch.Tensor
		"""
        device = "cuda" if torch.cuda.is_available() else "cpu"
        support = torch.mm(input_feature, self.weight.to(device))
        output = torch.sparse.mm(adjacency, support)
        if self.use_bias:
            output += self.bias.to(device)
        return output

    def __repr__(self):
        return self.__class__.__name__ + ' (' + str(self.in_features) + ' -> ' + str(self.out_features) + ')'

"""
define model
"""
class GcnNet(nn.Module):
    
    def __init__(self, input_dim=128):
        super(GcnNet, self).__init__()
        self.gcn1 = GraphConvolution(input_dim, 16)
        self.gcn2 = GraphConvolution(16, 4)
    
    def forward(self, adjacency, feature):
        h = F.relu(self.gcn1(adjacency, feature))
        logits = self.gcn2(adjacency, h)
        return logits

#train the model
learning_rate = 0.1
weight_decay = 5e-4
epochs = 500

#define some arguments
device = "cuda" if torch.cuda.is_available() else "cpu"
model = GcnNet().to(device)
criterion = nn.CrossEntropyLoss().to(device)
optimizer = optim.Adam(model.parameters(), lr=learning_rate, weight_decay=weight_decay)

adjacency, features, labels, train_mask, val_mask, test_mask= load_data()
tensor_x = features.to(device)
tensor_y = labels.to(device)
tensor_train_mask = torch.from_numpy(train_mask).to(device)
tensor_val_mask = torch.from_numpy(val_mask).to(device)
tensor_test_mask = torch.from_numpy(test_mask).to(device)
indices = torch.from_numpy(np.asarray([adjacency.row, adjacency.col]).astype('int64')).long()
values = torch.from_numpy(adjacency.data.astype(np.float32))
tensor_adjacency = torch.sparse.FloatTensor(indices, values, (22470, 22470)).to(device)

#train function
def train():
    loss_history = []
    val_acc_history = []
    model.train()
    train_y = tensor_y[tensor_train_mask]
    for epoch in range(epochs):
        logits = model(tensor_adjacency, tensor_x)
		#only choose node to train
        train_mask_logits = logits[tensor_train_mask]
        loss = criterion(train_mask_logits, train_y) 
        optimizer.zero_grad()
        loss.backward()    
        optimizer.step() 
        train_acc, _, _ = test(tensor_train_mask)
        val_acc, _, _ = test(tensor_val_mask)
        loss_history.append(loss.item())
        val_acc_history.append(val_acc.item())
        print("Epoch {:03d}: Loss {:.4f}, TestAcc {:.4}, TrainAcc {:.4f}".format(
            epoch, loss.item(), train_acc.item(), val_acc.item()))

def test(mask):
    model.eval()
    with torch.no_grad():
        logits = model(tensor_adjacency, tensor_x)
        test_mask_logits = logits[mask]
        predict_y = test_mask_logits.max(1)[1]
        accuarcy = torch.eq(predict_y, tensor_y[mask]).float().mean()
    return accuarcy, test_mask_logits.cpu().numpy(), tensor_y[mask].cpu().numpy()

train()

"""
TSNE part for embeddings plot.
"""
from sklearn.manifold import TSNE
test_accuracy, test_data, test_labels = test(tensor_test_mask)
tsne = TSNE(perplexity=30, n_components=2, init='pca', n_iter=5000)
low_dim_embs = tsne.fit_transform(test_data)
plt.title('tsne result')
plt.scatter(low_dim_embs[:,0], low_dim_embs[:,1], marker='o', c=test_labels)
plt.savefig("tsne.png")
