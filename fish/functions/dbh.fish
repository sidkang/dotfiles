function dbh --wraps='xattr -w com.dropbox.ignored 1' --description 'alias dbh xattr -w com.dropbox.ignored 1'
    xattr -w com.dropbox.ignored 1 $argv
end
