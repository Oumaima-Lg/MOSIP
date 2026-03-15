import sys
content = open('/home/mosip/configure_start.sh').read()
content = content.replace('sudo ./install.sh', './install.sh')
content = content.replace('mkdir "$DIR_NAME"', 'rm -rf "$DIR_NAME"; mkdir "$DIR_NAME"')
open('/home/mosip/configure_start.sh', 'w').write(content)
print("Done")
