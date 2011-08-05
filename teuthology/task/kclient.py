import contextlib
import logging
import os

from teuthology import misc as teuthology

log = logging.getLogger(__name__)

@contextlib.contextmanager
def task(ctx, config):
    """
    Mount/unmount a ``kernel`` client.

    The config is optional and defaults to mounting on all clients. If
    a config is given, it is expected to be a list of clients to do
    this operation on. This lets you e.g. set up one client with
    ``cfuse`` and another with ``kclient``.

    Example that mounts all clients::

        tasks:
        - ceph:
        - kclient:
        - interactive:

    Example that uses both ``kclient` and ``cfuse``::

        tasks:
        - ceph:
        - cfuse: [client.0]
        - kclient: [client.1]
        - interactive:
    """
    log.info('Mounting kernel clients...')
    assert config is None or isinstance(config, list), \
        "task kclient got invalid config"

    if config is None:
        config = ['client.{id}'.format(id=id_)
                  for id_ in teuthology.all_roles_of_type(ctx.cluster, 'client')]

    clients = teuthology.get_clients(ctx=ctx, config=config)
    for id_, remote in clients:
        log.debug('Mounting client client.{id}...'.format(id=id_))
        remotes_and_roles = ctx.cluster.remotes.items()
        roles = [roles for (remote_, roles) in remotes_and_roles]
        ips = [host for (host, port) in (remote_.ssh.get_transport().getpeername() for (remote_, roles) in remotes_and_roles)]
        mons = teuthology.get_mons(roles, ips).values()
        mnt = os.path.join('/tmp/cephtest', 'mnt.{id}'.format(id=id_))
        secret = '/tmp/cephtest/data/client.{id}.secret'.format(id=id_)
        teuthology.write_secret_file(remote, 'client.{id}'.format(id=id_), secret)

        remote.run(
            args=[
                'mkdir',
                '--',
                mnt,
                ],
            )

        remote.run(
            args=[
                'sudo',
                '/tmp/cephtest/enable-coredump',
                '/tmp/cephtest/binary/usr/local/bin/ceph-coverage',
                '/tmp/cephtest/archive/coverage',
                '/tmp/cephtest/binary/usr/local/sbin/mount.ceph',
                '{mons}:/'.format(mons=','.join(mons)),
                mnt,
                '-v',
                '-o',
                'name={id},secretfile={secret}'.format(id=id_,
                                                       secret=secret),
                ],
            )

    try:
        yield
    finally:
        log.info('Unmounting kernel clients...')
        for id_, remote in clients:
            log.debug('Unmounting client client.{id}...'.format(id=id_))
            mnt = os.path.join('/tmp/cephtest', 'mnt.{id}'.format(id=id_))
            remote.run(
                args=[
                    'sudo',
                    'umount',
                    mnt,
                    ],
                )
            remote.run(
                args=[
                    'rmdir',
                    '--',
                    mnt,
                    ],
                )
