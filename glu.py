import parse as p
import compile as c

import imp

def parse(s):
	return p.parse(s)

def build(s):
	return p.build(s)

def compile(s):
	return c.compile(build(s))

def exec(s):
	return compile(s)()

def reload():
	imp.reload(p.tokenize.pb)
	imp.reload(p.tokenize)
	imp.reload(p.code)
	imp.reload(p)
	imp.reload(c.cpy3compile)
	imp.reload(c)