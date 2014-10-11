import parse as p
import compile as c

import imp

def parse(s):
	return p.parse(s)

def flatten(s):
	return p.flatten(s)

def build(s):
	return p.build(s)

def compile(s,target="cpy3"):
	return c.compile(build(s),target)

def exec(s):
	return compile(s)()

def reload():
	imp.reload(p.tokenize.pb)
	imp.reload(p.tokenize)
	imp.reload(p.code)
	imp.reload(p.ast)
	imp.reload(p)
	imp.reload(c.cpy3compile)
	imp.reload(c.snowcompile)
	imp.reload(c)