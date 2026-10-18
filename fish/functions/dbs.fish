function dbs --wraps='xattr -d com.dropbox.ignored' --description 'alias dbs xattr -d com.dropbox.ignored'
    xattr -d com.dropbox.ignored $argv
end
