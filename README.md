## EPOS VP/VS Service

microservice enabling retrieval of VP/VS data

## Installation

Clone the github repo
```
git clone https://github.com/mlmarius/epos_vpvs.git
```

then cd into the installation dir
```
cd epos_vpvs
```

make sure all requirements are installed
```
pip install -r requirements.txt
```

now copy or move the config file
```
mv config.ini.sample config.ini
```

Dont't forget to edit config.ini and replace your own config details

Now run the app
```
python vpvs.py
```

You should now be able to access the app on port 8888
