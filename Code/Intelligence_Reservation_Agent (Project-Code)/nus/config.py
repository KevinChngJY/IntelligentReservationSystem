import configparser


default_config_file_path = 'config.ini'


def read(config_file=default_config_file_path):
    config = configparser.ConfigParser()
    config.read(config_file)
    return config

def read_db(config_file=default_config_file_path):
    config = read(config_file)
    return config['DB']['path'], config['DB']['table_est'], config['DB']['table_pat'], config['DB']['table_rsv'], config['DB']['table_qry']


def read_return_dict(section, config_file=default_config_file_path):
    config = read(config_file)
    return config[section]


if __name__ == '__main__':
    # to run as script
    pass
    # config = configparser.ConfigParser()
    # config['DEFAULT'] = {}
    # config['DB'] = {}
    # config['DB']['path'] = 'dummy.db'
    # config['DB']['table_est'] = 'dummy_est'
    # config['DB']['table_pat'] = 'dummy_pat'
    # config['DB']['table_rsv'] = 'dummy_rsv'
    # with open('config.ini', 'w') as configfile:
    #     config.write(configfile)
else:
    # to run during import
    pass
