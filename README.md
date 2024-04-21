# Shelltool

Shelltool is an api that makes dealing with and composing subprocesses in python easier, more readable, and more immediately useful.  It accomplishes this by utilizing syntax that makes it feel more like composing procedures in Bash rather than dealing with things like `Popen` or `Thread(target=lambda:subprocess.run())`.

Heres an example of the syntax.  
```py
if __name__ == "__main__":

    process = ~(SHELL.cat("./shelltool.py") | SHELL.grep("SHELL"))
    
    # This is the same as running the following command on a separate thread:
    # cat "./shelltool.py" | grep "SHELL"

    process.run()
    # .run() starts the process, or in this case the thread with running the process

    # The process joins the current thread when the attributes `stdout` or `stderr` are accessed
    print(f"result:\n{process.stdout.decode()}")
```

# How to Shelltool Your Python

Shelltool has a couple of syntax and operators that may look familiar for helping you write quick and functional Bash-like code.

## Composing a Command

To compose a command with Shelltool, first import the `SHELL`:

```py
from shelltool import SHELL
```

Next, choose an executable or command to run:

```py
SHELL.grep
# or
SHELL["grep"]
# or
SHELL["/path/to/grep binary"]
```

Next, pass your arguments to your executable or command:

```py
SHELL.grep("SHELL", "./shelltool.py")
# or
SHELL["grep"]("SHELL", "./shelltool.py")
# or
SHELL["/path/to/grep binary"]("SHELL", "./shelltool.py")
```

Then, run your shell executable or command:

```py
SHELL.grep("SHELL", "./shelltool.py").run()
# or
SHELL["grep"]("SHELL", "./shelltool.py").run()
# or
SHELL["/path/to/grep binary"]("SHELL", "./shelltool.py").run()
```

Finally, get all the data you need from your executable or command:

```py
grep_cmd = SHELL.grep("SHELL", "./shelltool.py").run()
# or
grep_cmd = SHELL["grep"]("SHELL", "./shelltool.py").run()
# or
grep_cmd = SHELL["/path/to/grep binary"]("SHELL", "./shelltool.py").run()

grep_cmd.stdout # the stdout of your process
grep_cmd.stderr # the stderr of your process
grep_cmd.pid # the pid of your process
```

## The Pipe Operators

`|` and `@`

The *Pipe* operators work the same as how they do in Bash:

The `|` operator is the same as `|` in Bash.  It pipes the stdout of the left hand side of the operator into the stdin of the right hand side of the operator.

```py
cat_to_grep_cmd = SHELL.cat("./shelltool.py") | SHELL.grep("SHELL")
cat_to_grep_cmd.run()

print(cat_to_grep_cmd.stdout.decode())
```

It works with any datatype on the left hand side that has a `__str__` dunder.

```py
cat_to_grep_cmd = "SHELL is\nso\nCOOL!" | SHELL.grep("SHELL")
cat_to_grep_cmd.run()

print(cat_to_grep_cmd.stdout.decode())
```

The `@` operator pipes the stderr of the left hand side of the operator into the stdin of the right hand side of the operator.

```py
cat_to_grep_cmd = SHELL.SHELL() @ SHELL.grep("SHELL")
cat_to_grep_cmd.run()

print(cat_to_grep_cmd.stdout.decode())
```

## The Tilda Operator

`~`

The *Tilda* operator runs the supplied process on a separate thread:

```py
# Lets pretend we need to run a slow subprocess.

# By just adding a tilda, we can instantly move this subprocess to a separate concurrent thread.
cat_to_grep_cmd = ~(SHELL.cat("./shelltool.py") | SHELL.grep("SHELL"))

# Now lets run our slow subprocess/spawn our thread.
cat_to_grep_cmd.run()

# Now that our process is happening off of the main thread we can do other computations while we wait for it to finish
while cat_to_grep_cmd.running:
    # do some other tasks...
    print(f"Currently doing concurrent tasks while running subprocess with pid: {cat_to_grep_cmd.pid}")

# Finally we've finished our other tasks, so lets get our long awaited stdout and stderr data from our subprocess.  Accessing either stdout or stderr on our process will join our thread back to its spawning thread, or in this case the main thread.
print(cat_to_grep_cmd.stdout.decode())
print(cat_to_grep_cmd.stderr.decode())
```

## Help! My subprocess is out of controll! (How to Kill Your Subprocess) 

Killing your rogue subprocess is as simple as `.kill()`.

```py
cat_to_grep_cmd = ~(SHELL.cat("./shelltool.py") | SHELL.grep("SHELL"))
cat_to_grep_cmd.run()

cat_to_grep_cmd.kill() # RIP subprocess ;(

print(cat_to_grep_cmd.stdout.decode())
```

## What If I Want My Subprocess's pid?

Getting a subprocess's pid is as simple as `.pid`.

```py
cat_to_grep_cmd = ~(SHELL.cat("./shelltool.py") | SHELL.grep("SHELL"))
cat_to_grep_cmd.run()

print(cat_to_grep_cmd.pid) # Here it is!

print(cat_to_grep_cmd.stdout.decode())
```

## Uh Oh! Race conditions! (How To Join a Concurrent Subprocess Back To It's Spawning Thread)

To join a subprocess back to its spawning thread call `.finish()`:
```py
process, process_err = ~((p1 := (SHELL.echo("SHELL") | SHELL.tee("/dev/stderr"))) | SHELL.grep("SHELL")), ~(p1 @ SHELL.grep("SHELL"))
process.run()

process.finish()
# this joins the thread/process so `p1` and the rest of `process` is evaluated before `p1` is used to evaluate `process_err`.

process_err.run()

print(f"p_out:\n{process.stdout.decode()}")
print(f"p_err:\n{process_err.stdout.decode()}")
```

***Side note***, you could also fix this specific race condition without calling `.finish()` by running `p1` before `process` and `process_err`:

```py
process, process_err = ~((p1 := (SHELL.echo("SHELL") | SHELL.tee("/dev/stderr"))) | SHELL.grep("SHELL")), ~(p1 @ SHELL.grep("SHELL"))
p1.run()
process.run()
process_err.run()

print(f"p_out:\n{process.stdout.decode()}")
print(f"p_err:\n{process_err.stdout.decode()}")
```