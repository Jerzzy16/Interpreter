###
🧩 Overview
###
This project is a simple interpreter for a hypothetical programming language called HL
The interpreter reads .HL source files, removes whitespace, identifies reserved words and symbols, executes the program, and reports whether any syntax or runtime errors occurred.

###
⚙️ Requirements
###
Python 3.7 or later

The files must be in the same folder:

interpreter.py
PROG1.HL
PROG2.HL
PROG3.HL

###
▶️ How to Run
###
Open a terminal or command prompt.

Navigate to the folder containing all files:

cd path/to/your/folder


Run any .HL program using:

python interpreter.py PROG1.HL


or (depending on your system)

py interpreter.py PROG1.HL

###
📄 Expected Outputs
###
PROG1.HL
x: integer;
x:= 5;
output<<x;


Terminal output:

5
NO ERROR(S) FOUND


Generated files:

NOSPACES.TXT → x:integer;x:=5;output<<x;

RES_SYM.TXT → lists: integer, output, :, ;, :=, <<

PROG2.HL
x: integer;
y: double;
x:= 3;
y:= 1.25;
output<<x+y;


Terminal output:

4.25
NO ERROR(S) FOUND

PROG3.HL
x: integer;
y: double;
x:= 3;
if(x<5) output<<x;


Terminal output:

3
NO ERROR(S) FOUND

###
🧾 Output Files Description
###
File	Description
NOSPACES.TXT	Version of the HL source code with all whitespace removed
RES_SYM.TXT	List of reserved words and symbols found in the program
Terminal Output	Displays the result of output<<...; statements and “NO ERROR(S) FOUND” if program runs successfully

###
⚠️ Notes
###
The interpreter only supports one-line if statements (e.g. if(x<5) output<<x;).

Use semicolons (;) to end every statement.

Variable types supported: integer and double.

Supported operations: +, -, comparison operators (<, >, ==, !=).
