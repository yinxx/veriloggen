Veriloggen
==============================

[![Build Status](https://travis-ci.org/PyHDI/veriloggen.svg)](https://travis-ci.org/PyHDI/veriloggen)

A library for constructing a Verilog HDL source code in Python

Copyright (C) 2015, Shinya Takamaeda-Yamazaki

E-mail: takamaeda\_at\_ist.hokudai.ac.jp


License
==============================

Apache License 2.0
(http://www.apache.org/licenses/LICENSE-2.0)


Publication
==============================

If you use Veriloggen in your research, please cite my paper about Pyverilog. (Veriloggen is constructed on Pyverilog.)

- Shinya Takamaeda-Yamazaki: Pyverilog: A Python-based Hardware Design Processing Toolkit for Verilog HDL, 11th International Symposium on Applied Reconfigurable Computing (ARC 2015) (Poster), Lecture Notes in Computer Science, Vol.9040/2015, pp.451-460, April 2015.
[Paper](http://link.springer.com/chapter/10.1007/978-3-319-16214-0_42)

```
@inproceedings{Takamaeda:2015:ARC:Pyverilog,
title={Pyverilog: A Python-Based Hardware Design Processing Toolkit for Verilog HDL},
author={Takamaeda-Yamazaki, Shinya},
booktitle={Applied Reconfigurable Computing},
month={Apr},
year={2015},
pages={451-460},
volume={9040},
series={Lecture Notes in Computer Science},
publisher={Springer International Publishing},
doi={10.1007/978-3-319-16214-0_42},
url={http://dx.doi.org/10.1007/978-3-319-16214-0_42},
}
```


What's Veriloggen?
==============================

Veriloggen is an open-sourced library for constructing a Verilog HDL source code in Python.

Veriloggen is not a behavior synthesis (or high level synthesis). Veriloggen provides a lightweight abstraction of Verilog HDL AST. You can build up a hardware design written in Verilog HDL very easily by using the AST abstraction and the entire functionality of Python.
 
Veriloggen is not designed for designing a hardware by programmer directly, but is for providing an efficient abstraction to develop a more efficient domain specific language and tools.


Installation
==============================

Requirements
--------------------

- Python: 2.7, 3.5 or later

Python3 is recommended.

- Icarus Verilog: 0.9.7 or later (but 10.0 is not recommended)

Install on your platform. For exmple, on Ubuntu:

    sudo apt-get install iverilog

- Jinja2: 2.8 or later

Install on your python environment by using pip:

    pip install jinja2

- Pyverilog: 1.1.1 or later

Install from pip (or download and install from GitHub):

    pip install pyverilog

- IPgen: 0.3.1 or later

Install from pip (or download and install from GitHub):

    pip install ipgen

Options
--------------------

- pytest: 2.8.2 or later
- pytest-pythonpath: 0.7 or later

These softwares are required for running the tests in tests and examples:

    pip install pytest pytest-pythonpath

- Graphviz: 2.38.0 or later
- Pygraphviz: 1.3.1 or later

These softwares are required for graph visualization by veriloggen.dataflow:

    sudo apt-get install graphviz
    pip install pygraphviz

- NumPy: 1.14 or later

This is required for the memory image generation function of types.axi.AxiMemoryModel from Python list or numpy.ndarray:

    pip install numpy

Install
--------------------

Install Veriloggen:

    python setup.py install

On Docker
--------------------

Dockerfile is available, so that you can try Veriloggen on Docker without any installation on your host platform.

```
cd docker
sudo docker build -t user/veriloggen .
sudo docker run --name veriloggen -i -t user/veriloggen /bin/bash
cd veriloggen/examples/led/
make
```


Getting Started
==============================

You can find some examples in 'veriloggen/examples/' and 'veriloggen/tests'.

Let's begin veriloggen by an example. Create a example Python script in Python as below. A blinking LED hardware is modeled in Python.
Open 'hello_led.py' in the root directory.

```python
from __future__ import absolute_import
from __future__ import print_function
import sys
import os
from veriloggen import *


def mkLed():
    m = Module('blinkled')
    width = m.Parameter('WIDTH', 8)
    clk = m.Input('CLK')
    rst = m.Input('RST')
    led = m.OutputReg('LED', width, initval=0)
    count = m.Reg('count', 32, initval=0)

    seq = Seq(m, 'seq', clk, rst)

    seq.If(count == 1024 - 1)(
        count(0)
    ).Else(
        count.inc()
    )

    seq.If(count == 1024 - 1)(
        led.inc()
    )

    seq(
        Systask('display', "LED:%d count:%d", led, count)
    )

    return m


def mkTest():
    m = Module('test')

    # target instance
    led = mkLed()

    uut = Submodule(m, led, name='uut')
    clk = uut['CLK']
    rst = uut['RST']

    simulation.setup_waveform(m, uut, m.get_vars())
    simulation.setup_clock(m, clk, hperiod=5)
    init = simulation.setup_reset(m, rst, m.make_reset(), period=100)

    init.add(
        Delay(1000 * 100),
        Systask('finish'),
    )

    return m

if __name__ == '__main__':
    test = mkTest()
    verilog = test.to_verilog(filename='tmp.v')
    #verilog = test.to_verilog()
    print(verilog)

    sim = simulation.Simulator(test)
    rslt = sim.run()
    print(rslt)

    # sim.view_waveform()
```

Run the script.

```
python hello_led.py
```

You will have a complete Verilog HDL source code named 'tmp.v' as below, which is generated by the source code generator.

```verilog
module test
(

);

  localparam uut_WIDTH = 8;
  reg uut_CLK;
  reg uut_RST;
  wire [uut_WIDTH-1:0] uut_LED;

  blinkled
  uut
  (
    .CLK(uut_CLK),
    .RST(uut_RST),
    .LED(uut_LED)
  );


  initial begin
    $dumpfile("uut.vcd");
    $dumpvars(0, uut, uut_CLK, uut_RST, uut_LED);
  end


  initial begin
    uut_CLK = 0;
    forever begin
      #5 uut_CLK = !uut_CLK;
    end
  end


  initial begin
    uut_RST = 0;
    #100;
    uut_RST = 1;
    #100;
    uut_RST = 0;
    #100000;
    $finish;
  end


endmodule



module blinkled #
(
  parameter WIDTH = 8
)
(
  input CLK,
  input RST,
  output reg [WIDTH-1:0] LED
);

  reg [32-1:0] count;

  always @(posedge CLK) begin
    if(RST) begin
      count <= 0;
      LED <= 0;
    end else begin
      if(count == 1023) begin
        count <= 0;
      end else begin
        count <= count + 1;
      end
      if(count == 1023) begin
        LED <= LED + 1;
      end 
      $display("LED:%d count:%d", LED, count);
    end
  end


endmodule
```

You will also see the simulation result of the generated Verilog code on Icarus Verilog.

```
VCD info: dumpfile uut.vcd opened for output.
LED:  x count:         x
LED:  x count:         x
LED:  x count:         x
LED:  x count:         x
LED:  x count:         x
LED:  x count:         x
LED:  x count:         x
LED:  x count:         x
LED:  x count:         x
LED:  x count:         x
LED:  0 count:         0
LED:  0 count:         1
LED:  0 count:         2
LED:  0 count:         3
LED:  0 count:         4
...
LED:  9 count:       777
LED:  9 count:       778
LED:  9 count:       779
LED:  9 count:       780
LED:  9 count:       781
LED:  9 count:       782
LED:  9 count:       783
```

If you installed GTKwave and enable 'sim.view_waveform()' in 'hello_led.py', you can see the waveform the simulation result.

![waveform.png](img/waveform.png)


Veriloggen Extension Libraries
==============================

### Mixed-Paradigm High-Level Synthesis

- veriloggen.thread.Thread: Procedural high-level synthesis for DMA and I/O controls
- veriloggen.thread.Stream: Dataflow-based high-level synthesis for high-performance stream processing

### Frequently-used Abstractions

- veriloggen.verilog: Verilog HDL source code synthesis and import APIs
- veriloggen.simulation: Simulation APIs via Verilog simulators
- veriloggen.seq: Synchronous circuit builder (Seq)
- veriloggen.fsm: Finite state machine builder (FSM)

Please see examples and tests directories for many examples.


Related Project
==============================

[Pyverilog](https://github.com/PyHDI/Pyverilog)
- Python-based Hardware Design Processing Toolkit for Verilog HDL

[IPgen](https://github.com/PyHDI/ipgen)
- IP-core package generator for AXI4/Avalon
