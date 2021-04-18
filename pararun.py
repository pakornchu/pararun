#!/usr/bin/env python3

import queue
import threading
import subprocess
import sys
import logging
import traceback
import argparse
import json
import os.path
import time
import datetime
import random

THREADS = 2
LOCKRETRY = 3


def logqfmt(msg=None, cmd=None, delayed=False):
    if msg is not None:
        return "%s %-10s %s\n" % (
            datetime.datetime.now().isoformat(),
            f"[{cmd.strip()}]{'*' if delayed else ''}",
            msg
            )


def lockandwrite(lockobj=None, datasrc=[], dstfile=None,
                 fallbackq=None, context='unknown'):
    if lockobj is not None and dstfile is not None and fallbackq is not None:
        logacquirecount = 0
        while logacquirecount < LOCKRETRY:
            acquired = lockobj.acquire(0)
            if acquired:
                fc = open(dstfile, 'a')
                for i in datasrc:
                    fc.write(logqfmt(i, context))
                fc.flush()
                fc.close()
                lockobj.release()
                break
            else:
                logging.warning('Unable to acquire logfile lock')
                logacquirecount += 1
                time.sleep(random.randrange(0, 1000) * .001)
        if logacquirecount >= LOCKRETRY:
            for i in datasrc:
                logq.put(logqfmt(i, context, True))


def Worker(q=None, logq=None, lockobj=None, stdoutlog=None):
    logging.info(f'Thread started')
    while True:
        data = q.get()
        if data is not None and type(data) is dict:
            cmd = data['cmd'].split(' ')
            try:
                po = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                logging.info(f"Executing {data['cmd']}")
                po.wait()
                cmdoutput = po.stdout.read()
                lockandwrite(lockobj, cmdoutput.decode('utf-8').strip().split('\n'), stdoutlog, logq, data['name'])
                fc = open(f"{data['logdir']}/{data['name']}-{time.strftime('%Y%m%d')}.log", 'a')
                fc.write(cmdoutput.decode('utf-8'))
                fc.close()
                logging.info(f"Completed {data['cmd']}")
            except:
                logging.critical(f"Unable to execute {data['cmd']}")
                lockandwrite(lockobj, traceback.format_exc().strip().split('\n'), stdoutlog, logq, data['name'])
            if not all(i is None for i in list(q.queue)):
                logging.info(f"{len(q.queue)} job(s) left in this queue")
            q.task_done()
        else:
            logging.info('No more job for this worker, terminating')
            break


def terminate(jobq=None, threads=None):
    for i in range(THREADS):
        jobq.put(None)

    for i in threads:
        i.join()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("cmdfile")
    parser.add_argument('--logdir', help='Log path, default to curdir', default=os.path.abspath(os.path.curdir))
    parser.add_argument('--masterlog', help='Master error log path, default to curdir', default=f'{os.path.abspath(os.path.curdir)}/master.log')
    parser.add_argument('--mastererrlog', help='Master error log path, default to curdir', default=f'{os.path.abspath(os.path.curdir)}/mastererror.log')
    parser.add_argument('--threads', help="Number of threads")
    parser.add_argument('--lockretry', help="Lock acquisition attempts before writequeue fallback")
    args = parser.parse_args()
    if not os.path.isfile(args.cmdfile):
        logging.critical(f'CMDFILE {args.cmdfile} not found')
        sys.exit(1)

    if not os.path.isdir(args.logdir):
        logging.critical(f'LOGDIR {args.logdir} not found')
        sys.exit(2)

    if not os.path.isdir(os.path.dirname(args.mastererrlog)):
        logging.critical(f'MASTERERRLOG directory not found')
        sys.exit(3)

    if not os.path.isdir(os.path.dirname(args.masterlog)):
        logging.critical(f'MASTERLOG directory not found')
        sys.exit(4)

    logformat = '%(asctime)s %(levelname)-9s [%(threadName)s] %(message)s'
    logging.basicConfig(filename=args.masterlog, level=logging.INFO, format=logformat)
    logger = logging.getLogger()
    consolelog = logging.StreamHandler()
    formatter = logging.Formatter(logformat)
    consolelog.setFormatter(formatter)
    logger.addHandler(consolelog)

    if args.threads is not None:
        try:
            THREADS = int(args.threads)
        except:
            logging.warning(f'Fallback to default {THREADS} thread(s)')

    if args.lockretry is not None:
        try:
            LOCKRETRY = int(args.lockretry)
        except:
            logging.warning(f'Fallback to default {LOCKRETRY} lock acquisition attempts')

    fc = open(os.path.abspath(args.cmdfile), 'r')
    rawdata = fc.read()
    fc.close()

    LOCK = threading.Lock()

    try:
        cmdlist = json.loads(rawdata)
    except:
        logging.critical(f'Unable to parse CMDFILE. Must be in [{{"cmd":"xxx", "name": "yyy"}},...] format')
        sys.exit(1)

    logging.info(f"Logging output to {args.logdir}")
    jobq = queue.Queue()
    logq = queue.Queue()
    threads = []
    for i in range(THREADS):
        thobj = threading.Thread(target=Worker, args=(jobq, logq, LOCK, args.mastererrlog))
        thobj.start()
        threads.append(thobj)

    for i in cmdlist:
        i['logdir'] = args.logdir
        jobq.put(i)

    while True:
        if jobq.empty():
            terminate(jobq, threads)
            fc = open(args.mastererrlog, 'a')
            while logq.qsize():
                item = logq.get()
                if type(item) is bytes:
                    fc.write(item.decode('utf-8'))
                elif type(item) is str:
                    fc.write(item)
            fc.close()
            logging.info(f'Master logs {args.masterlog}')
            logging.info(f'Master error logs {args.mastererrlog}')
            sys.exit(0)
