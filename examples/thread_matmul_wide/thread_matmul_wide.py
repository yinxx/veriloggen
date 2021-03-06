from __future__ import absolute_import
from __future__ import print_function
import sys
import os
import numpy as np

# the next line can be removed after installation
sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

from veriloggen import *
import veriloggen.thread as vthread
import veriloggen.types.axi as axi

axi_wordsize = 8
data_wordsize = 4

a_offset = 0
b_offset = 4096
c_offset = 4096 * 2


def mkLed(matrix_size=16):
    m = Module('blinkled')
    clk = m.Input('CLK')
    rst = m.Input('RST')

    seq = Seq(m, 'seq', clk, rst)
    timer = m.Reg('timer', 32, initval=0)
    seq(
        timer.inc()
    )

    datawidth = 32
    addrwidth = 10
    ram_a = vthread.RAM(m, 'ram_a', clk, rst, datawidth, addrwidth)
    ram_b = vthread.RAM(m, 'ram_b', clk, rst, datawidth, addrwidth)
    ram_c = vthread.RAM(m, 'ram_c', clk, rst, datawidth, addrwidth)
    myaxi = vthread.AXIM(m, 'myaxi', clk, rst, datawidth * (axi_wordsize // data_wordsize))

    def matmul(matrix_size, a_offset, b_offset, c_offset):
        start_time = timer
        comp(matrix_size, a_offset, b_offset, c_offset)
        end_time = timer
        time = end_time - start_time
        print("Time (cycles): %d" % time)
        check(matrix_size, a_offset, b_offset, c_offset)
        vthread.finish()

    def comp(matrix_size, a_offset, b_offset, c_offset):
        a_addr, c_addr = a_offset, c_offset

        for i in range(matrix_size):
            myaxi.dma_read(ram_a, 0, a_addr, matrix_size)

            b_addr = b_offset
            for j in range(matrix_size):
                myaxi.dma_read(ram_b, 0, b_addr, matrix_size)

                sum = 0
                for k in range(matrix_size):
                    x = ram_a.read(k)
                    y = ram_b.read(k)
                    sum += x * y
                ram_c.write(j, sum)

                b_addr += matrix_size * (datawidth // 8)

            myaxi.dma_write(ram_c, 0, c_addr, matrix_size)
            a_addr += matrix_size * (datawidth // 8)
            c_addr += matrix_size * (datawidth // 8)

    def check(matrix_size, a_offset, b_offset, c_offset):
        all_ok = True
        c_addr = c_offset
        for i in range(matrix_size):
            myaxi.dma_read(ram_c, 0, c_addr, matrix_size)
            for j in range(matrix_size):
                v = ram_c.read(j)
                if i == j and vthread.verilog.NotEql(v, (i + 1) * 2):
                    all_ok = False
                    print("NG [%d,%d] = %d" % (i, j, v))
                if i != j and vthread.verilog.NotEql(v, 0):
                    all_ok = False
                    print("NG [%d,%d] = %d" % (i, j, v))
            c_addr += matrix_size * (datawidth // 8)

        if all_ok:
            print('# verify: PASSED')
        else:
            print('# verify: FAILED')

    th = vthread.Thread(m, 'th_matmul', clk, rst, matmul)
    fsm = th.start(matrix_size, a_offset, b_offset, c_offset)

    return m


def mkTest(memimg_name=None):
    matrix_size = 16

    a_shape = (matrix_size, matrix_size)
    b_shape = (matrix_size, matrix_size)
    c_shape = (a_shape[0], b_shape[0])

    n_raw_a = axi.shape_to_length(a_shape)
    n_raw_b = axi.shape_to_length(b_shape)

    n_a = axi.memory_word_length(a_shape, data_wordsize)
    n_b = axi.memory_word_length(b_shape, data_wordsize)

    #a = np.arange(n_raw_a, dtype=np.int32).reshape(a_shape)
    #b = np.arange(n_raw_b, dtype=np.int32).reshape(b_shape) + [n_a]
    a = np.zeros(a_shape, dtype=np.int64)
    b = np.zeros(b_shape, dtype=np.int64)

    value = 1
    for y in range(a_shape[0]):
        for x in range(a_shape[1]):
            if x == y:
                a[y][x] = value
                value += 1
            else:
                a[y][x] = 0

    for y in range(b_shape[0]):
        for x in range(b_shape[1]):
            if x == y:
                b[y][x] = 2
            else:
                b[y][x] = 0

    a_addr = a_offset
    size_a = n_a * data_wordsize
    b_addr = b_offset
    size_b = n_b * data_wordsize

    mem = np.zeros([1024 * 1024 // axi_wordsize], dtype=np.int64)
    axi.set_memory(mem, a, axi_wordsize, data_wordsize, a_addr)
    axi.set_memory(mem, b, axi_wordsize, data_wordsize, b_addr)

    led = mkLed(matrix_size)

    m = Module('test')
    params = m.copy_params(led)
    ports = m.copy_sim_ports(led)
    clk = ports['CLK']
    rst = ports['RST']

    memory = axi.AxiMemoryModel(m, 'memory', clk, rst,
                                datawidth=8 * axi_wordsize,
                                mem_datawidth=8 * axi_wordsize,
                                memimg=mem, memimg_name=memimg_name)

    memory.connect(ports, 'myaxi')

    uut = m.Instance(led, 'uut',
                     params=m.connect_params(led),
                     ports=m.connect_ports(led))

    simulation.setup_waveform(m, uut)
    simulation.setup_clock(m, clk, hperiod=5)
    init = simulation.setup_reset(m, rst, m.make_reset(), period=100)

    init.add(
        Delay(1000000),
        Systask('finish'),
    )

    return m


def run(filename='tmp.v', simtype='iverilog', outputfile=None):

    if outputfile is None:
        outputfile = os.path.splitext(os.path.basename(__file__))[0] + '.out'

    memimg_name = 'memimg_' + outputfile

    test = mkTest(memimg_name=memimg_name)

    if filename is not None:
        test.to_verilog(filename)

    sim = simulation.Simulator(test, sim=simtype)
    rslt = sim.run(outputfile=outputfile)
    lines = rslt.splitlines()
    if simtype == 'verilator' and lines[-1].startswith('-'):
        rslt = '\n'.join(lines[:-1])
    return rslt


if __name__ == '__main__':
    rslt = run(filename='tmp.v')
    print(rslt)
