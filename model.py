import tensorflow as tf
import numpy as np
from data_preprocess import read_data
import sys

tf.set_random_seed(7)

class MemN2N(object):
    def __init__(self, config, sess):
        self.batch_size = config['batch_size']
        self.emb_dim = config['emb_dim']
        self.mem_size = config['mem_size']
        self.is_test = config['test']
        self.n_epoch = config['n_epoch']
        self.n_hop = config['n_hop']
        self.n_words = config['n_words']
        self.lr = config['lr']
        self.std_dev = config['std_dev']
        self.optim = tf.train.AdamOptimizer(self.lr)
        
        self.inp_X = tf.placeholder('int32',[self.batch_size, self.mem_size])
        self.inp_Y = tf.placeholder('int32', [self.batch_size,])
        self.time = tf.placeholder('int32', [self.batch_size, self.mem_size])    
        self.loss = None  
        self.session = sess

    def init_model(self):
        # Input and output embeddings
        i_emb   = tf.Variable(tf.random_normal([self.n_words, self.emb_dim], stddev=self.std_dev), dtype='float32')
        o_emb   = tf.Variable(tf.random_normal([self.n_words, self.emb_dim], stddev=self.std_dev), dtype='float32')
        # Input and output embedding for time information
        i_emb_T = tf.Variable(tf.random_normal([self.n_words, self.emb_dim], stddev=self.std_dev), dtype='float32')
        o_emb_T = tf.Variable(tf.random_normal([self.n_words, self.emb_dim], stddev=self.std_dev), dtype='float32')
        # Query fixed to a vector of 0.1
        initial_q   = tf.constant(0.1, shape=[self.batch_size, self.emb_dim], dtype='float32')
        # For linear mapping of u between hops
        Aw = tf.Variable(tf.random_normal([self.emb_dim, self.emb_dim], stddev=self.std_dev), dtype='float32')
        Ab = tf.Variable(tf.random_normal([self.emb_dim], stddev=self.std_dev), dtype='float32')
        #For storing the final layer of each hop
        hid = []
        hid.append(initial_q)
        # Final weight matrix
        W = tf.Variable(tf.random_normal([self.n_words, self.emb_dim], stddev=self.std_dev), dtype='float32')

        #Memory vectors
        mem_C = tf.nn.embedding_lookup(i_emb, self.inp_X)
        mem_T = tf.nn.embedding_lookup(i_emb_T, self.time)
        mem = tf.add(mem_C, mem_T)

        #Output vectors
        out_C = tf.nn.embedding_lookup(o_emb, self.inp_X)
        out_T = tf.nn.embedding_lookup(o_emb, self.time)
        out = tf.add(out_C, out_T)

        for hop in range(self.n_hop):
            hid3d = tf.reshape(hid[-1], [-1, self.emb_dim, 1])
            probs = tf.nn.softmax(tf.batch_matmul(mem, hid3d))
            o = tf.batch_matmul(out, probs, adj_x=True)
            sigma_uo = tf.add(hid3d, o)
            hid2d = tf.reshape(sigma_uo, [-1, self.emb_dim])
            Cout = tf.add(tf.matmul(hid2d, Aw), Ab) 
            hid.append(Cout)
        
        z = tf.matmul(hid[-1], W, transpose_b=True)
        self.loss = tf.nn.sparse_softmax_cross_entropy_with_logits(z, self.inp_Y)
        self.train_op = self.optim.minimize(self.loss)
        tf.initialize_all_variables().run()

    def train(self, train_data, valid_data):
        self.init_model()
        #TODO : Merge train and test into a single function
        N = int((len(train_data)/self.batch_size)+1)
        t = np.ndarray([self.batch_size, self.mem_size])
        
        for x in range(0, self.mem_size):
            t[:, x].fill(x)

        for epoch in range(self.n_epoch):
            total_loss = 0
            for n in range(N):
                inputs = []
                targets = []
                for item in range(self.batch_size):
                    mark = np.random.randint(self.mem_size+1, len(train_data))
                    next_word = train_data[mark]
                    prec_words = train_data[mark-self.mem_size : mark]
                    inputs.append(prec_words)
                    targets.append(next_word)
                inputs = np.asarray(inputs)
                targets = np.asarray(targets)
            
                fd = {
                    self.inp_X : inputs,
                    self.inp_Y : targets,
                    self.time : t
                }
                _, batch_loss = self.session.run([self.train_op, self.loss], feed_dict=fd)
                
                total_loss += np.sum(batch_loss)
                cost = total_loss/(n*self.batch_size)
                perp = np.exp(cost)
                print "cost",cost, "Perp:",perp,"--",n,"/",N 
            print
            print "Train Perplexity :",np.exp(cost/(N*self.batch_size))
            print 
            self.test(valid_data)

    def test(self, data):
            # self.init_model()

            N = int((len(data)/self.batch_size)+1)
            t = np.ndarray([self.batch_size, self.mem_size])
            
            for x in range(0, self.mem_size):
                t[:, x].fill(x)

        
            total_loss = 0
            for n in range(N):
                inputs = []
                targets = []
                for item in range(self.batch_size):
                    mark = np.random.randint(self.mem_size+1, len(data))
                    next_word = data[mark]
                    prec_words = data[mark-self.mem_size : mark]
                    inputs.append(prec_words)
                    targets.append(next_word)
                inputs = np.asarray(inputs)
                targets = np.asarray(targets)
            
                fd = {
                    self.inp_X : inputs,
                    self.inp_Y : targets,
                    self.time : t
                }

                batch_loss = self.session.run([self.loss], feed_dict=fd)
                total_loss += np.sum(batch_loss)
                cost = total_loss/(n*self.batch_size)
                perp = np.exp(cost)
                # print "cost",cost, "Perp:",perp,"--",n+1,"/",N
                sys.stdout.write('.')
                sys.stdout.flush() 

            print
            print "Test Perplexity :",perp
            print 