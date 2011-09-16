import logging
import os

from teuthology import misc as teuthology
from teuthology.parallel import parallel
from ..orchestra import run

log = logging.getLogger(__name__)

def task(ctx, config):
    """
    Run ceph all workunits found under the specified path.

    For example::

        tasks:
        - ceph:
        - cfuse: [client.0]
        - workunit:
            client.0: [direct_io, xattrs.sh]
            client.1: [snaps]

    You can also run a list of workunits on all clients:
        tasks:
        - ceph:
        - cfuse:
        - workunit:
            all: [direct_io, xattrs.sh, snaps]

    If you have an "all" section it will run all the workunits
    on each client simultaneously, AFTER running any workunits specified
    for individual clients. (This prevents unintended simultaneous runs.)
    """
    assert isinstance(config, dict)

    log.info('Making a separate scratch dir for every client...')
    for role in config.iterkeys():
        assert isinstance(role, basestring)
        if role == "all":
            continue
        PREFIX = 'client.'
        assert role.startswith(PREFIX)
        _make_scratch_dir(ctx, role)
    all_spec = False #is there an all grouping?
    with parallel() as p:
        for role, tests in config.iteritems():
            if role != "all":
                p.spawn(_run_tests, ctx, role, tests)
            else:
                all_spec = True

    if all_spec:
        all_tasks = config["all"]
        _spawn_on_all_clients(ctx, all_tasks)

def _make_scratch_dir(ctx, role):
    PREFIX = 'client.'
    id_ = role[len(PREFIX):]
    log.debug("getting remote for {id} role {role_}".format(id=id_, role_=role))
    (remote,) = ctx.cluster.only(role).remotes.iterkeys()
    mnt = os.path.join('/tmp/cephtest', 'mnt.{id}'.format(id=id_))
    remote.run(
        args=[
            # cd first so this will fail if the mount point does
            # not exist; pure install -d will silently do the
            # wrong thing
            'cd',
            '--',
            mnt,
            run.Raw('&&'),
            'sudo',
            'install',
            '-d',
            '-m', '0755',
            '--owner={user}'.format(user='ubuntu'), #TODO
            '--',
            'client.{id}'.format(id=id_),
            ],
        )

def _spawn_on_all_clients(ctx, tests):
    client_generator = teuthology.all_roles_of_type(ctx.cluster, 'client')
    client_remotes = list()
    for client in client_generator:
        (client_remote,) = ctx.cluster.only('client.{id}'.format(id=client)).remotes.iterkeys()
        client_remotes.append((client_remote, 'client.{id}'.format(id=client)))
        _make_scratch_dir(ctx, "client.{id}".format(id=client))
        
    for unit in tests:
        with parallel() as p:
            for remote, role in client_remotes:
                p.spawn(_run_tests, ctx, role, [unit])

def _run_tests(ctx, role, tests):
    assert isinstance(role, basestring)
    PREFIX = 'client.'
    assert role.startswith(PREFIX)
    id_ = role[len(PREFIX):]
    (remote,) = ctx.cluster.only(role).remotes.iterkeys()
    mnt = os.path.join('/tmp/cephtest', 'mnt.{id}'.format(id=id_))
    # subdir so we can remove and recreate this a lot without sudo
    scratch_tmp = os.path.join(mnt, 'client.{id}'.format(id=id_), 'tmp')
    srcdir = '/tmp/cephtest/workunit.{role}'.format(role=role)

    remote.run(
        logger=log.getChild(role),
        args=[
            'mkdir', '--', srcdir,
            run.Raw('&&'),
            'wget',
            '-q',
            '-O-',
            # TODO make branch/tag/sha1 used configurable
            'https://github.com/NewDreamNetwork/ceph/tarball/HEAD',
            run.Raw('|'),
            'tar',
            '-C', srcdir,
            '-x',
            '-z',
            '-f-',
            '--wildcards',
            '--no-wildcards-match-slash',
            '--strip-components=3',
            '--',
            '*/qa/workunits/',
            run.Raw('&&'),
            'cd', '--', srcdir,
            run.Raw('&&'),
            'if', 'test', '-e', 'Makefile', run.Raw(';'), 'then', 'make', run.Raw(';'), 'fi',
            run.Raw('&&'),
            'find', '-executable', '-type', 'f', '-printf', r'%P\0'.format(srcdir=srcdir),
            run.Raw('>/tmp/cephtest/workunits.list'),
            ],
        )

    workunits = sorted(teuthology.get_file(remote, '/tmp/cephtest/workunits.list').split('\0'))
    assert workunits

    try:
        assert isinstance(tests, list)
        for spec in tests:
            log.info('Running workunits matching %s on %s...', spec, role)
            prefix = '{spec}/'.format(spec=spec)
            to_run = [w for w in workunits if w == spec or w.startswith(prefix)]
            if not to_run:
                raise RuntimeError('Spec did not match any workunits: {spec!r}'.format(spec=spec))
            for workunit in to_run:
                log.info('Running workunit %s...', workunit)
                remote.run(
                    logger=log.getChild(role),
                    args=[
                        'mkdir', '--', scratch_tmp,
                        run.Raw('&&'),
                        'cd', '--', scratch_tmp,
                        run.Raw('&&'),
                        run.Raw('PATH="$PATH:/tmp/cephtest/binary/usr/local/bin"'),
                        run.Raw('LD_LIBRARY_PATH="$LD_LIBRARY_PATH:/tmp/cephtest/binary/usr/local/lib"'),
                        run.Raw('CEPH_CONF="/tmp/cephtest/ceph.conf"'),
                        '/tmp/cephtest/enable-coredump',
                        '/tmp/cephtest/binary/usr/local/bin/ceph-coverage',
                        '/tmp/cephtest/archive/coverage',
                        '{srcdir}/{workunit}'.format(
                            srcdir=srcdir,
                            workunit=workunit,
                            ),
                        run.Raw('&&'),
                        'rm', '-rf', '--', scratch_tmp,
                        ],
                    )
    finally:
        remote.run(
            logger=log.getChild(role),
            args=[
                'rm', '-rf', '--', '/tmp/cephtest/workunits.list', srcdir,
                ],
            )
