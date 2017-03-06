#!/usr/bin/python3
import aiohttp
import asyncio
import optparse
import os
import sys
import time
import urllib.parse

PARALLEL = 5

class Downloader:

    @asyncio.coroutine
    def download_into(self, url, filename, build_id):
        print("Download %s" % url)
        response = yield from aiohttp.request('GET', url)
        if response.status != 200:
            print("HTTP error %s: %s" % (response.status, url))
            response.close()
            return

        with open(filename, 'wb') as fp:
            # FIXME: stream
            content = yield from response.read()
            fp.write(content)
        if not content:
            print("ERROR: empty HTTP body: %s" % url)
            return

        return build_id

    def parse_options(self):
        parser = optparse.OptionParser(usage="%prog [options] slave_name build_id")
        parser.add_option("-a", "--all",
            help="Download all builds",
            action="store_true", default=False)
        parser.add_option("-n", "--last", metavar="N",
            help="Download the last N builds (default: 1)",
            type="int", default=1)
        options, args = parser.parse_args()
        if len(args) != 2:
            parser.print_help()
            exit(1)

        slave, build_id = args
        try:
            build_id = int(build_id)
        except ValueError:
            print("Invalid build identifier: %r" % build_id)
        return options, slave, build_id


    def _main(self):
        start_time = time.monotonic()
        options, slave, build_id = self.parse_options()

        directory = slave.replace(" ", "_")
        try:
            os.mkdir(directory)
        except OSError:
            pass

        first_build_id = build_id
        last_build_id = None
        tasks = set()
        todo = options.last
        while 1 <= build_id:
            url = "http://buildbot.python.org/all/builders/%s/builds/%s/steps/test/logs/stdio/text" % (urllib.parse.quote(slave), build_id)
            # TODO: use a keep-alive connection to the web server
            filename = os.path.join(directory, str(build_id))
            if not os.path.exists(filename):
                task = asyncio.async(self.download_into(url, filename, build_id))
                tasks.add(task)

                if len(tasks) > PARALLEL:
                    # limit the number of parallel tasks
                    wait = asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                    done, tasks = yield from wait

                    task = next(iter(done))
                    if not task.result():
                        # a download failed
                        if options.all:
                            break
                    else:
                        task_build_id = task.result()
                        if task_build_id is not None:
                            if last_build_id is not None:
                                last_build_id = min(last_build_id, task_build_id)
                            else:
                                last_build_id = task_build_id

            if not options.all:
                todo -= 1
                if todo < 1:
                    break
            build_id -= 1

        if tasks:
            done, pending = yield from asyncio.wait(tasks)
            for task in done:
                task_build_id = task.result()
                if task_build_id is not None:
                    if last_build_id is not None:
                        last_build_id = min(last_build_id, task_build_id)
                    else:
                        last_build_id = task_build_id

        if not last_build_id:
            print("Nothing was downloaded")
            sys.exit(1)

        dt = time.monotonic() - start_time
        if last_build_id != first_build_id:
            text = "builds #%s..#%s (%s)" % (last_build_id, first_build_id, first_build_id - last_build_id + 1)
        else:
            text = "build #%s" % first_build_id
        print("Downloaded %s into %s in %.1f sec" % (text, directory, dt))

    def main(self):
        self.loop = asyncio.get_event_loop()
        self.loop.run_until_complete(self._main())


if __name__ == "__main__":
    Downloader().main()
