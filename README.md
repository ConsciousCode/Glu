## Glu

An incomplete language being designed for the compilation of arbitrary languages in the same environment. The intent of this project is to add enough features that it can compile its own source to Python bytecode and recursively add features.

Glu supports:
 * Basic arithmetic (+ - * /)
 * Signed integer and floating point constants
 * Label and goto keywords
 * Return keyword
 * If statement
 * Python target
 * Comments
   - Single line: #...
   - Multi line: #( ... )# (supports nesting)

Glu assembly supports:
 * add(a,b) sub(a,b) mul(a,b) div(a,b) neg(x)
 * goto(label) ifnot(cond,label) return(ret)
 * alias(x)

Glu assembly has the following syntax:
> number = ["-"], {digit}, [".", {digit}];
> ident = {letter | digit | "_" | "$"};
> reg = "%", ident;
> label = "#", ident;
>
> value = number | reg;
>
> arith = reg "=" (("add" | "sub" | "mul" | "div") value value | "neg" value);
> control = "goto" label | "return" value | "ifnot" value label;
> misc = "nop" | reg "=" "alias" value;
>
> program = {arith | control | misc};