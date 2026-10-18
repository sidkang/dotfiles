-- Load necessary Hammerspoon modules
local repo_path = "/path/to/your/repo" -- Replace with your repository path

local function runGitCommand(path, args)
	local git, _, _, _ = hs.execute("which git", true)
	hs.task
		.new(git, nil, function(task, stdOut, stdErr)
			print("Pulling from remote:", stdOut, stdErr)
		end, hs.fnutils({ "-C", path }, args))
		:start()
end

-- Function to pull from remote
local function gitPull()
	hs.task
		.new("/usr/bin/git", nil, function(task, stdOut, stdErr)
			print("Pulling from remote:", stdOut, stdErr)
		end, { "-C", repo_path, "pull" })
		:start()
end

-- Function to add, commit, and push changes
local function gitCommitAndPush()
	hs.task
		.new("/usr/bin/git", nil, function(task, stdOut, stdErr)
			print("Adding changes:", stdOut, stdErr)
			hs.task
				.new("/usr/bin/git", nil, function(task, stdOut, stdErr)
					print("Committing changes:", stdOut, stdErr)
					hs.task
						.new("/usr/bin/git", nil, function(task, stdOut, stdErr)
							print("Pushing to remote:", stdOut, stdErr)
						end, { "-C", repo_path, "push" })
						:start()
				end, { "-C", repo_path, "commit", "-m", "Auto-commit by Hammerspoon" })
				:start()
		end, { "-C", repo_path, "add", "." })
		:start()
end

-- Watcher to track file changes
local function fileChangeWatcher(paths, flagTables)
	if not hs.timer.delayed._delayedCommit then
		hs.timer.delayed._delayedCommit = hs.timer.delayed.new(60, gitCommitAndPush)
	end
	hs.timer.delayed._delayedCommit:start()
end

-- Setup path watcher
local pathwatcher = hs.pathwatcher.new(repo_path, fileChangeWatcher):start()

-- Timer to pull from remote every 10 minutes
local pullTimer = hs.timer.doEvery(600, gitPull)

-- Start the initial pull immediately
gitPull()

git, _, _, _ = hs.execute("which git", true)
task = hs.task.new(git, nil, function(task, stdOut, stdErr)
	print("Pulling from remote:", stdOut, stdErr)
end, hs.fnutils.concat({ "-C", os.getenv("HOME") .. "/logseq" }, { "status" }))

task:start()
