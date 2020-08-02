# Content Automation Scripts

Content pipeline automation scripts -- everything is *fab*ulous when you've got Python on your side.



Install
-------

    virtualenv -p python3 venv
    source venv/bin/activate
    pip install -r requirements.txt


 


Further developments and possible niceties:
  - Start using an inventory.json to store the info from gcp.inventory
    - Automatically read when fab runs
    - Automatically append to when new demoservers created
    - Automatically remove when demoserver deleted
  - Make sure swap space persists after reboot (see TODO in install_base)

