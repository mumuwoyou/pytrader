# coding: utf-8
import numpy as np
import tensorflow as tf
from .FixPonderDNCore import DNCore_L3
from .FixPonderDNCore import ResidualACTCore as ACTCore


class Classifier_PonderDNC_BasicLSTM_L3(object):

    def __init__(self,
                 inputs,
                 targets,
                 gather_list=None,
                 mini_batch_size=1,
                 hidden_size=10,
                 memory_size=10,
                 threshold=0.99,
                 pondering_coefficient=1e-2,
                 num_reads=3,
                 num_writes=1,
                 learning_rate=1e-4,
                 optimizer_epsilon=1e-10,
                 max_gard_norm=50):

        self._tmp_inputs = inputs
        self._tmp_targets = targets
        self._in_length = None
        self._in_width = inputs.shape[2]
        self._out_length = None
        self._out_width = targets.shape[2]
        self._mini_batch_size = mini_batch_size
        self._batch_size = inputs.shape[1]

        # 声明计算会话
        self._sess = tf.InteractiveSession()

        self._inputs = tf.placeholder(dtype=tf.float32,
                                      shape=[self._in_length, self._batch_size, self._in_width],
                                      name='inputs')
        self._targets = tf.placeholder(dtype=tf.float32,
                                       shape=[self._out_length, self._batch_size, self._out_width],
                                       name='targets')

        act_core = DNCore_L3(hidden_size=hidden_size,
                             memory_size=memory_size,
                             word_size=self._in_width,
                             num_read_heads=num_reads,
                             num_write_heads=num_writes)
        self._InferenceCell = ACTCore(core=act_core,
                                      output_size=self._out_width,
                                      threshold=threshold,
                                      get_state_for_halting=self._get_hidden_state)

        self._initial_state = self._InferenceCell.initial_state(self._batch_size)

        tmp, act_final_cumul_state = \
            tf.nn.dynamic_rnn(cell=self._InferenceCell,
                              inputs=self._inputs,
                              initial_state=self._initial_state,
                              time_major=True)
        act_output, (act_final_iteration, act_final_remainder) = tmp

        # 测试
        self._final_iteration = tf.reduce_mean(act_final_iteration)

        self._act_output = act_output
        if gather_list is not None:
            out_sequences = tf.gather(act_output, gather_list)
        else:
            out_sequences = act_core

        # 设置损失函数
        pondering_cost = (act_final_iteration + act_final_remainder) * pondering_coefficient
        rnn_cost = tf.nn.softmax_cross_entropy_with_logits(
            labels=self._targets, logits=out_sequences)
        self._pondering_cost = tf.reduce_mean(pondering_cost)
        self._rnn_cost = tf.reduce_mean(rnn_cost)
        self._cost = self._pondering_cost + self._rnn_cost
        self._pred = tf.nn.softmax(out_sequences, dim=2)
        correct_pred = tf.equal(tf.argmax(self._pred, 2), tf.argmax(self._targets, 2))
        self._accuracy = tf.reduce_mean(tf.cast(correct_pred, tf.float32))

        # 设置优化器
        # Set up optimizer with global norm clipping.
        trainable_variables = tf.trainable_variables()
        grads, _ = tf.clip_by_global_norm(
            tf.gradients(self._cost, trainable_variables), max_gard_norm)
        global_step = tf.get_variable(
            name="global_step",
            shape=[],
            dtype=tf.int64,
            initializer=tf.zeros_initializer(),
            trainable=False,
            collections=[tf.GraphKeys.GLOBAL_VARIABLES, tf.GraphKeys.GLOBAL_STEP])

        optimizer = tf.train.RMSPropOptimizer(
            learning_rate=learning_rate, epsilon=optimizer_epsilon)
        self._train_step = optimizer.apply_gradients(
            zip(grads, trainable_variables), global_step=global_step)

        # 待处理函数

    def _get_hidden_state(self, state):
        controller_state, access_state, read_vectors = state
        layer_1, layer_2, layer_3 = controller_state
        L1_next_state, L1_next_cell = layer_1
        L2_next_state, L2_next_cell = layer_2
        L3_next_state, L3_next_cell = layer_3
        return tf.concat([L1_next_state, L2_next_state, L3_next_state], axis=-1)

    def fit(self,
            training_iters=1e2,
            display_step=5,
            save_path=None,
            restore_path=None):

        self._sess.run(tf.global_variables_initializer())
        # 保存和恢复
        self._variables_saver = tf.train.Saver()
        if restore_path is not None:
            self._variables_saver.restore(self._sess, restore_path)

        if self._batch_size == self._mini_batch_size:
            for scope in range(np.int(training_iters)):
                _, loss, acc, tp1, tp2, tp3 = \
                    self._sess.run([self._train_step,
                                    self._cost,
                                    self._accuracy,
                                    self._pondering_cost,
                                    self._rnn_cost,
                                    self._final_iteration],
                                   feed_dict={self._inputs: self._tmp_inputs, self._targets: self._tmp_targets})
                # 显示优化进程
                if scope % display_step == 0:
                    print(scope,
                          '  loss--', loss,
                          '  acc--', acc,
                          '  pondering_cost--', tp1,
                          '  rnn_cost--', tp2,
                          '  final_iteration', tp3)
                    # 保存模型可训练变量
                    if save_path is not None:
                        self._variables_saver.save(self._sess, save_path)

            print("Optimization Finished!")
        else:
            print('未完待续')

    def close(self):
        self._sess.close()
        print('结束进程，清理tensorflow内存/显存占用')

    def pred(self, inputs, gather_list=None, restore_path=None):
        if restore_path is not None:
            self._sess.run(tf.global_variables_initializer())
            self._variables_saver = tf.train.Saver()
            self._variables_saver.restore(self._sess, restore_path)

        output_pred = self._act_output
        if gather_list is not None:
            output_pred = tf.gather(output_pred, gather_list)
        probability = tf.nn.softmax(output_pred)
        classification = tf.argmax(probability, axis=-1)

        return self._sess.run([probability, classification], feed_dict={self._inputs: inputs})

    def restore_trainable_variables(self, restore_path):
        if restore_path is not None:
            self._sess.run(tf.global_variables_initializer())
            self._variables_saver = tf.train.Saver()
            self._variables_saver.restore(self._sess, restore_path)

    def score(self, inputs, targets, gather_list=None):
        acc = self._sess.run(
            self._accuracy,
            feed_dict={self._inputs: self._tmp_inputs,
                       self._targets: self._tmp_targets})
        return acc