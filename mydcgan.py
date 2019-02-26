# 导入需要的包
from PIL import Image  # Image 用于读取影像
from skimage import io  # io也可用于读取影响，效果比Image读取的更好一些

import tensorflow as tf  # 用于构建神经网络模型
import matplotlib.pyplot as plt  # 用于绘制生成影像的结果
import numpy as np  # 读取影像
import os  # 文件夹操作
import time  # 计时

# 设置相关参数
is_training = True
input_dir = "./face/"  # 原始数据的文件夹路径

# 设置超参数 hyper parameters
batch_size = 64
image_width = 64
image_height = 64
image_channel = 3
data_shape = [64, 64, 3]
data_length = 64 * 64 * 3

z_dim = 100
learning_rate = 0.00005
beta1 = 0.5
epoch = 500


# 读取数据的函数
def prepare_data(input_dir, floder):
    '''
    函数功能：通过输入图像的路径，读取训练数据
    :参数 input_dir: 图像数据所在的根目录，即"./face"
    :参数 floder: 图像数据所在的子目录, 即"./face/A"
    :return: 返回读取好的训练数据
    '''

    # 遍历图像路径，并获取图像数量
    images = os.listdir(input_dir + floder)
    image_len = len(images)

    # 设置一个空data，用于存放数据
    data = np.empty((image_len, image_width, image_height, image_channel), dtype="float32")

    # 逐个图像读取
    for i in range(image_len):
        # 如果导入的是skimage.io，则读取影像应该写为img = io.imread(input_dir + images[i])
        img = Image.open(input_dir + floder + "/" + images[i])  # 打开图像
        img = img.resize((image_width, image_height))  # 将256*256变成64*64
        arr = np.asarray(img, dtype="float32")  # 将格式改为np.array
        data[i, :, :, :] = arr  # 将其放入data中

    sess = tf.Session()
    sess.run(tf.initialize_all_variables())
    data = tf.reshape(data, [-1, image_width, image_height, image_channel])
    train_data = data * 1.0 / 127.5 - 1.0  # 对data进行正则化
    train_data = tf.reshape(train_data, [-1, data_length])  # 将其拉伸成一维向量
    train_set = sess.run(train_data)
    sess.close()
    return train_set


# 定义生成器
def Generator(z, is_training, reuse):
    '''
    函数功能：输入噪声z，生成图像gen_img
    :param z:即输入数据，一般为噪声
    :param is_training:是否为训练环节
    :return: 返回生成影像gen_img
    '''

    # 图像的channel维度变化为1->1024->512->256->128->3
    depths = [1024, 512, 256, 128] + [data_shape[2]]

    with tf.variable_scope("Generator", reuse=reuse):
        # 第一层全连接层
        with tf.variable_scope("g_fc1", reuse=reuse):
            output = tf.layers.dense(z, depths[0] * 4 * 4, trainable=is_training)
            output = tf.reshape(output, [batch_size, 4, 4, depths[0]])
            output = tf.nn.relu(tf.layers.batch_normalization(output, training=is_training))

        # 第二层反卷积层1024
        with tf.variable_scope("g_dc1", reuse=reuse):
            output = tf.layers.conv2d_transpose(output, depths[1], [5, 5], strides=(2, 2),
                                                padding="SAME", trainable=is_training)
            output = tf.nn.relu(tf.layers.batch_normalization(output, training=is_training))

        # 第三层反卷积层512
        with tf.variable_scope("g_dc2", reuse=reuse):
            output = tf.layers.conv2d_transpose(output, depths[2], [5, 5], strides=(2, 2),
                                                padding="SAME", trainable=is_training)
            output = tf.nn.relu(tf.layers.batch_normalization(output, training=is_training))

        # 第四层反卷积层256
        with tf.variable_scope("g_dc3", reuse=reuse):
            output = tf.layers.conv2d_transpose(output, depths[3], [5, 5], strides=(2, 2),
                                                padding="SAME", trainable=is_training)
            output = tf.nn.relu(tf.layers.batch_normalization(output, training=is_training))

        # 第五层反卷积层128
        with tf.variable_scope("g_dc4", reuse=reuse):
            output = tf.layers.conv2d_transpose(output, depths[4], [5, 5], strides=(2, 2),
                                                padding="SAME", trainable=is_training)
            gen_img = tf.nn.tanh(output)

    return gen_img


# 定义判别器
def Discriminator(x, is_training, reuse):
    '''
    函数功能：判别输入的图像是真或假
    :param x: 输入数据
    :param is_training: 是否为训练环节
    :return: 判别结果
    '''

    # 生成器的channel维度变化为：3->64->128->256->512
    depths = [data_shape[2]] + [64, 128, 256, 512]

    with tf.variable_scope("Discriminator", reuse=reuse):
        # 第一层卷积层，注意用的是leaky_relu函数
        with tf.variable_scope("d_cv1", reuse=reuse):
            output = tf.layers.conv2d(x, depths[1], [5, 5], strides=(2, 2),
                                      padding="SAME", trainable=is_training)
            output = tf.nn.leaky_relu(tf.layers.batch_normalization(output, training=is_training))

        # 第二层卷积层，注意用的是leaky_relu函数
        with tf.variable_scope("d_cv2", reuse=reuse):
            output = tf.layers.conv2d(output, depths[2], [5, 5], strides=(2, 2),
                                      padding="SAME", trainable=is_training)
            output = tf.nn.leaky_relu(tf.layers.batch_normalization(output, training=is_training))

        # 第三层卷积层，注意用的是leaky_relu函数
        with tf.variable_scope("d_cv3", reuse=reuse):
            output = tf.layers.conv2d(output, depths[3], [5, 5], strides=(2, 2),
                                      padding="SAME", trainable=is_training)
            output = tf.nn.leaky_relu(tf.layers.batch_normalization(output, training=is_training))

        # 第四层卷积层，注意用的是leaky_relu函数
        with tf.variable_scope("d_cv4", reuse=reuse):
            output = tf.layers.conv2d(output, depths[4], [5, 5], strides=(2, 2),
                                      padding="SAME", trainable=is_training)
            output = tf.nn.leaky_relu(tf.layers.batch_normalization(output, training=is_training))

        # 第五层全链接层
        with tf.variable_scope("d_fc1", reuse=reuse):
            output = tf.layers.flatten(output)
            disc_img = tf.layers.dense(output, 1, trainable=is_training)

    return disc_img


def plot_and_save(order, images):
    '''
    函数功能：绘制生成器的结果，并保存
    :param order:
    :param images:
    :return:
    '''

    # 将一个batch_size的所有图像进行保存
    batch_size = len(images)
    n = np.int(np.sqrt(batch_size))

    # 读取图像大小，并生成掩模canvas
    image_size = np.shape(images)[2]
    n_channel = np.shape(images)[3]
    images = np.reshape(images, [-1, image_size, image_size, n_channel])
    canvas = np.empty((n * image_size, n * image_size, image_channel))

    # 为每个掩模赋值
    for i in range(n):
        for j in range(n):
            canvas[i * image_size:(i + 1) * image_size, j * image_size:(j + 1) * image_size, :] = images[
                n * i + j].reshape(64, 64, 3)

    # 绘制结果，并设置坐标轴
    plt.figure(figsize=(8, 8))
    plt.imshow(canvas, cmap="gray")
    label = "Epoch: {0}".format(order + 1)
    plt.xlabel(label)

    # 为每个文件命名
    if type(order) is str:
        file_name = order
    else:
        file_name = "face_gen" + str(order)

    # 保存绘制的结果
    plt.savefig(file_name)
    print(os.getcwd())
    print("Image saved in file: ", file_name)
    plt.close()


# 定义训练过程
def training():
    '''
    函数功能：实现DCGAN的训练过程
    '''
    # 准备数据。这里输入根目录，以A的影像为例进行图像生成
    data = prepare_data(input_dir, "A")

    # 构建网络结构，这是程序的核心部分---------------------------------------------
    x = tf.placeholder(tf.float32, shape=[None, data_length], name="Input_data")
    x_img = tf.reshape(x, [-1] + data_shape)
    z = tf.placeholder(tf.float32, shape=[None, z_dim], name="latent_var")

    G = Generator(z, is_training=True, reuse=False)
    D_fake_logits = Discriminator(G, is_training=True, reuse=False)
    D_true_logits = Discriminator(x_img, is_training=True, reuse=True)

    # 定义生成器的损失函数G_loss
    G_loss = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(
        logits=D_fake_logits, labels=tf.ones_like(D_fake_logits)))

    # 定义判别器的损失函数D_loss
    D_loss_1 = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(
        logits=D_true_logits, labels=tf.ones_like(D_true_logits)))
    D_loss_2 = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(
        logits=D_fake_logits, labels=tf.zeros_like(D_fake_logits)))
    D_loss = D_loss_1 + D_loss_2

    # 定义方差
    total_vars = tf.trainable_variables()
    d_vars = [var for var in total_vars if "d_" in var.name]
    g_vars = [var for var in total_vars if "g_" in var.name]

    # 定义优化方式
    with tf.control_dependencies(tf.get_collection(tf.GraphKeys.UPDATE_OPS)):
        g_optimization = tf.train.AdamOptimizer(learning_rate=learning_rate,
                                                beta1=beta1).minimize(G_loss, var_list=g_vars)
        d_optimization = tf.train.AdamOptimizer(learning_rate=learning_rate,
                                                beta1=beta1).minimize(D_loss, var_list=d_vars)
    print("we successfully make the network")
    # 网络模型构建结束------------------------------------------------------------

    # 训练模型初始化
    start_time = time.time()  # 计时
    sess = tf.Session()
    sess.run(tf.initialize_all_variables())

    # 逐个epoch训练
    for i in range(epoch):
        total_batch = int(len(data) / batch_size)
        d_value = 0
        g_value = 0
        # 逐个batch训练
        for j in range(total_batch):
            batch_xs = data[j * batch_size:j * batch_size + batch_size]

            # 训练判别器
            z_sampled1 = np.random.uniform(low=-1.0, high=1.0, size=[batch_size, z_dim])
            Op_d, d_ = sess.run([d_optimization, D_loss], feed_dict={x: batch_xs, z: z_sampled1})

            # 训练生成器
            z_sampled2 = np.random.uniform(low=-1.0, high=1.0, size=[batch_size, z_dim])
            Op_g, g_ = sess.run([g_optimization, G_loss], feed_dict={x: batch_xs, z: z_sampled2})

            # 尝试生成影像并保存
            images_generated = sess.run(G, feed_dict={z: z_sampled2})
            d_value += d_ / total_batch
            g_value += g_ / total_batch
            plot_and_save(i, images_generated)

            # 输出时间和损失函数loss
            hour = int((time.time() - start_time) / 3600)
            min = int(((time.time() - start_time) - 3600 * hour) / 60)
            sec = int((time.time() - start_time) - 3600 * hour - 60 * min)
            print("Time: ", hour, "h", min, "min", sec, "sec", "   Epoch: ",
                  i, "G_loss: ", g_value, "D_loss: ", d_value)

if __name__ == "__main__":
    training()
