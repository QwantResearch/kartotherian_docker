#!/usr/bin/env python3

import subprocess
import time
import sys


COMMANDS = ["build", "load-db", "update-tiles", "shutdown", "logs", "kartotherian"]


def exec_command(command, options):
    if options.get('debug') is True:
        print('==> {}'.format(' '.join(command)))
    p = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT)
    while True:
        output = p.stdout.read1(100)
        # print('hello! {}'.format(len(output)))
        if len(output) == 0:
            rc = p.poll()
            if rc is not None:
                return rc
        if len(output) > 0:
            sys.stdout.buffer.write(output)
            sys.stdout.buffer.flush()


def run_kartotherian(options):
    print('> running kartotherian command')
    return exec_command([
        'docker-compose',
        'up',
        '--build',
        '-d',
    ], options)


def run_build(options):
    print('> running build command')
    return exec_command([
        'docker-compose',
        '-f', 'docker-compose.yml',
        '-f', 'local-compose.yml',
        'up',
        '--build',
        '-d',
    ], options)


def run_load_db(options):
    ret = run_build(options)
    if ret != 0:
        return ret
    time.sleep(5) # add into the script a function to check if postgresql is up
    print('> running load-db command')
    if options['osm-file'].startswith('https://') or options['osm-file'].startswith('http://'):
        flag = 'INVOKE_OSM_URL={}'.format(options['osm-file'])
    else:
        flag = 'INVOKE_OSM_FILE={}'.format(options['osm-file'])
    command = [
        'docker-compose',
        '-f', 'docker-compose.yml',
        '-f', 'local-compose.yml',
        'run', '--rm',
        '-e', flag,
    ]
    if options['tiles-x'] is not None:
        command.extend(['-e', 'INVOKE_TILES_X={}'.format(options['tiles-x'])])
    if options['tiles-y'] is not None:
        command.extend(['-e', 'INVOKE_TILES_Y={}'.format(options['tiles-y'])])
    if options['tiles-z'] is not None:
        command.extend(['-e', 'INVOKE_TILES_Z={}'.format(options['tiles-z'])])
    command.append('load_db')
    return exec_command(command, options)


def run_update_tiles(options):
    ret = run_load_db(options)
    if ret != 0:
        return ret
    print('> running update-tiles command')
    return exec_command([
        'docker-compose',
        '-f', 'docker-compose.yml',
        '-f', 'local-compose.yml',
        'run', '--rm',
        'load_db',
        'run-osm-update',
    ], options)


def run_shutdown(options):
    print('> running shutdown command')
    return exec_command([
        'docker-compose',
        '-f', 'docker-compose.yml',
        '-f', 'local-compose.yml',
        'down',
        '-v',
    ], options)


def run_logs(options):
    print('> running logs command')
    command = [
        'docker-compose',
        '-f', 'docker-compose.yml',
        '-f', 'local-compose.yml',
        'logs',
    ]
    for f in options['filter']:
        command.append(f)
    return exec_command(command, options)


def run_help():
    print('== katotherian_docker options ==')
    print('  build         : build basics')
    print('  kartotherian  : launch (and build) kartotherian')
    print('  load-db       : load data from the given `--osm-file-url` (luxembourg by default)')
    print('  update-tiles  : update the tiles data')
    print('  shutdown      : shutdown running docker instances')
    print('  logs          : show docker logs (can be filtered with `--filter` option)')
    print('  --debug       : show more information on the run')
    print('  --filter      : container to show on `logs` command')
    print('  --osm-file    : file or URL to be used for pbf file in `load-db`, luxembourg by default')
    print('  --tiles-x     : X position for tiles (default to 66)')
    print('  --tiles-y     : Y position for tiles (default to 43)')
    print('  --tiles-z     : Z position for tiles (default to 7)')
    print('  -h | --help   : show this help')
    sys.exit(0)


def parse_args(args):
    available_options = ['--no-dependency-run', '--debug']
    available_options.extend(COMMANDS)
    enabled_options = {
        'osm-file': 'https://download.geofabrik.de/europe/luxembourg-latest.osm.pbf',
        'filter': [],
        'tiles-x': 66,
        'tiles-y': 43,
        'tiles-z': 7,
    }
    i = 0
    while i < len(args):
        if args[i] in available_options:
            enabled_options[args[i]] = True
        elif args[i] == '--filter':
            if i + 1 >= len(args):
                print('`--filter` option expects an argument!')
                sys.exit(1)
            i += 1
            enabled_options[args[i - 1][2:]].append(args[i])
        elif args[i] == '--osm-file':
            if i + 1 >= len(args):
                print('`--osm-file` option expects an argument!')
                sys.exit(1)
            i += 1
            enabled_options[args[i - 1][2:]] = args[i]
        elif args[i] in ['--tiles-x', '--tiles-y', '--tiles-z']:
            if i + 1 >= len(args):
                print('`{}` option expects an argument!'.format(args[i]))
                sys.exit(1)
            i += 1
            if len(args[i]) < 1:
                enabled_options[args[i - 1][2:]] = None
            else:
                try:
                    float(args[i])
                except ValueError:
                    print('`{}` option expects a number!'.format(args[i - 1]))
                enabled_options[args[i - 1][2:]] = args[i]
        elif args[i] == '-h' or args[i] == '--help':
            run_help()
        else:
            print('Unknown option `{}`, run with with `-h` or `--help` to see the list of commands'
                .format(args[i]))
            sys.exit(1)
        i += 1
    return enabled_options


def main():
    definitions = globals()
    options = parse_args(sys.argv[1:])
    for key in options:
        if key in COMMANDS and options[key] is True:
            func_name = 'run_{}'.format(key.replace('-', '_'))
            ret = definitions[func_name](options)
            if ret != 0:
                print('{} command failed'.format(key))
                sys.exit(ret)


if __name__ == '__main__':
    main()
