import torch
import torch.nn as nn
import numpy as np
from joblib import Parallel, delayed
from approximate_multiplier import FP_appx_mul
import torch.nn.functional as F

class convAppx(torch.autograd.Function):

    @staticmethod
    def forward(ctx, X, weight, bias, padding, stride):
        #confs = torch.from_numpy(np.array([stride[0], padding[0]]))

        ctx.save_for_backward(X, weight, bias)        
        (m, n_C_prev, n_H_prev, n_W_prev) = X.shape
        (n_C, n_C_prev, f, f) = weight.shape

        n_H = ((n_H_prev - f + 2 * padding[0]) // stride[0]) + 1
        n_W = ((n_W_prev - f + 2 * padding[0]) // stride[0]) + 1

        def appx_mul(A,B):
            window = np.zeros((A.shape))
            for l in range(A.shape[0]):
              for j in range(A.shape[1]):
                for k in range(A.shape[2]):
                  window[l,j,k] = FP_appx_mul(A[l,j,k],B[l,j,k])  #A[l,j,k]*B[l,j,k]
            return np.sum(window)

        def mul_channel( weight,bias, x_pad, n_H, n_W,f):
              Z = np.zeros(( n_H, n_W ))
              for h in range(n_H):
                  for w in range(n_W):
                      vert_start = h
                      vert_end = vert_start + f
                      horiz_start = w
                      horiz_end = horiz_start + f
            
                      x_slice = x_pad[:, vert_start:vert_end, horiz_start:horiz_end]  
                      Z[ h, w] = appx_mul(x_slice,weight)  #torch.matmul(A,B)
                      Z[ h, w] += bias
              return Z
      
        X_pad = F.pad(X, (padding[0],padding[0],padding[0],padding[0]))
        weight = weight.data.numpy()
        bias = bias.data.numpy()
        X_pad = X_pad.data.numpy()

        Z = np.zeros((m, n_C, n_H, n_W ))     
         
        for i in range(m):
          for c in range(n_C):
            Z[i,c] = mul_channel( weight[c, :, :, :],bias[c], X_pad[0], n_H, n_W, f) 
            #Using Joblib Parallel
            #Z[0] = Parallel(n_jobs=8)(delayed(mul_channel)( weight[c, :, :, :],bias[c], X_pad[0], n_H, n_W, f)  for c in  range(n_C) )
        return torch.from_numpy(Z).float()

    @staticmethod
    def backward(ctx, grad_output):
        x, weight, bias = ctx.saved_tensors 

        grad_input = grad_weight = grad_bias = None

        def convolutionBackward(dconv_prev, conv_in, weight, padding =1, stride=1):
            (m, n_C_prev, n_H_prev, n_W_prev) = conv_in.shape
            (n_C, n_C_prev, f, f) = weight.shape
            (m, n_C, n_H, n_W) = dconv_prev.shape

            dA_prev = torch.zeros((m, n_C_prev, n_H_prev, n_W_prev))
            dW = torch.zeros((n_C, n_C_prev, f, f))
            db = torch.zeros((n_C))
            X_pad = F.pad(conv_in, (padding,padding,padding,padding))
            dA_prev_pad = F.pad(dA_prev, (padding,padding,padding,padding))

            for i in range(m):
                x_pad = X_pad[i]
                da_prev_pad = dA_prev_pad[i]
              
                for c in range(n_C):
                    for h in range(n_H):
                        for w in range(n_W):
                            vert_start = h + h * (stride - 1)
                            vert_end = vert_start + f
                            horiz_start = w + w * (stride - 1)
                            horiz_end = horiz_start + f

                            x_slice = x_pad[:, vert_start:vert_end, horiz_start:horiz_end]

                            da_prev_pad[:, vert_start:vert_end, horiz_start:horiz_end] += weight[c, :, :, :] * dconv_prev[i, c, h, w]
                        
                            dW[c,:,:,:] += x_slice * dconv_prev[i, c, h, w]
                            
                            db[c] += dconv_prev[i, c, h, w]  
                if padding == 0:
                  dA_prev[i, :, :, :] = da_prev_pad[:]
                else:
                  dA_prev[i, :, :, :] = da_prev_pad[:, padding:-padding, padding:-padding] 
          
            return dA_prev, dW, db
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
        grad_input, grad_weight, grad_bias = convolutionBackward(grad_output, x, weight)
        grad_bias = grad_bias.squeeze()
        return grad_input, grad_weight, grad_bias, None,None   

class MyConv2d(nn.Module):
    def __init__(self, n_channels, out_channels, kernel_size , padding, stride, dilation=1):
        super(MyConv2d, self).__init__()

        self.kernel_size = (kernel_size, kernel_size)
        self.kernal_size_number = kernel_size * kernel_size
        self.out_channels = out_channels
        self.dilation = (dilation, dilation)
        self.padding = (padding, padding)
        self.stride = (stride, stride)
        self.n_channels = n_channels
        self.weight = nn.Parameter(torch.rand(self.out_channels, self.n_channels, self.kernel_size[0] , self.kernel_size[1] ))
        self.bias = nn.Parameter(torch.rand(self.out_channels))

    def forward(self, x):
        res = convAppx.apply(x, self.weight, self.bias, self.padding, self.stride)

        return res