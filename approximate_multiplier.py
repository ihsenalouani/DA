#Approximate 4x4 array multiplier (using the approximate mirror adder AMA5)
def appx_multiplier4x4_AMA5(A,B):

    S = 0
    if (A == 0) or (B == 0):
        S = 0
    elif (A == 1):
        S = B
    elif (A % 2 == 0) & (A>1):
        if (B < 8): 
            S = 0
        else:
            S = 32 * (A/2)
    else:
        if (B < 8): 
            S = B
        else:
            S = B + 32 * (A-1)/2
    return S  
    
#Approximate 8x8 array multiplier
def appx_multiplier8x8(a,b):

    a0b0 = appx_multiplier4x4_AMA5(int(a[4:8],2), int(b[4:8],2))
    a1b0 = appx_multiplier4x4_AMA5(int(a[0:4],2), int(b[4:8],2))
    a0b1 = appx_multiplier4x4_AMA5(int(a[4:8],2), int(b[0:4],2))
    a1b1 = appx_multiplier4x4_AMA5(int(a[0:4],2), int(b[0:4],2))
    S = (a0b0 + (a1b0 + a0b1)*16 + a1b1*256) 
    S = format(int(S), '016b')
    return S
    
#Approximate 24x24 array multiplier    
def appx_multiplier24x24(a,b):
    a0 = a[16:24]
    a1 = a[8:16]
    a2 = a[0:8]
    b0 = b[16:24]
    b1 = b[8:16]
    b2 = b[0:8]
    
    a0b0 = int(appx_multiplier8x8(a0,b0),2)
    a1b0 = int(appx_multiplier8x8(a1,b0),2)*256
    a2b0 = int(appx_multiplier8x8(a2,b0),2)*256*256
    a0b1 = int(appx_multiplier8x8(a0,b1),2)*256
    a1b1 = int(appx_multiplier8x8(a1,b1),2)*256*256
    a2b1 = int(appx_multiplier8x8(a2,b1),2)*256*256*256
    a0b2 = int(appx_multiplier8x8(a0,b2),2)*256*256
    a1b2 = int(appx_multiplier8x8(a1,b2),2)*256*256*256
    a2b2 = int(appx_multiplier8x8(a2,b2),2)*256*256*256*256
    
    S = a0b0 + a1b0 + a2b0 + a0b1 + a1b1 + a2b1 + a0b2 + a1b2 + a2b2
    S = format(S, '048b')
    return S
    
#Convert Decimal number to Floating Point number
import struct
def dec2FP(num):
    s = ''.join(bin(c).replace('0b', '').rjust(8, '0') for c in struct.pack('!f', num))    
    return s
    
#Convert Floating Point number to Decimal number
def FP2dec(n):
    #add subnormal numbers, for NaNs, for +/- infinity
    s = struct.unpack('!f',struct.pack('!I', int(n, 2)))[0]
    return s
    
#Approximate Floating Point multiplier    
def FP_appx_mul(A,B):
    if (abs(A)<1e-36) or (abs(B)<1e-36) or (A == 0) or (B==0):
        s = 0
    else:
        S = ['0','00000000','00000000000000000000000']
        a = dec2FP(A)
        b = dec2FP(B)
        sign_ab = int(a[0])^int(b[0])
        exponent_a = a[1:9]
        if int(exponent_a,2)>255:
            exponent_a = 255
        exponent_b = b[1:9]
        if int(exponent_a,2)>255:
            exponent_b = 255
        exponent_ab = int(exponent_a,2) + int(exponent_b,2) - 127
        if exponent_ab>255:
            exponent_ab = 255
        mantissa_ab = appx_multiplier24x24('1'+ a[9:32],'1'+ b[9:32])
        if mantissa_ab[0] == '1':
            final_mantissa = mantissa_ab[1:24]
            exponent_ab = exponent_ab + 1
        else:
            final_mantissa = mantissa_ab[2:25]
        S = [str(sign_ab), format(exponent_ab,'08b'), final_mantissa]
        S = ''.join(S)  
        s = FP2dec(S)
    return s 