import asmparse as p
import interpret as i
import compile as c

import imp

def parse(x):
	return p.parse(x)

def eval(x):
	return i.interpret(parse(x))

def compile(x):
	return c.compile(parse(x))

def exec(x):
	return compile(x)()

def reload():
	imp.reload(p)
	imp.reload(i)
	imp.reload(c)