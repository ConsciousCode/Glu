import gluasm as ga
import glu as g
import imp

def reload():
	imp.reload(ga)
	imp.reload(g)
	ga.reload()
	g.reload()