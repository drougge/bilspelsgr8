import yaml
def custom_str_constructor(loader, node):
  return loader.construct_scalar(node).encode('utf-8')

yaml.add_constructor(u'tag:yaml.org,2002:str', custom_str_constructor)

with open('settings.yaml') as f: 
	settings = yaml.load(f)
