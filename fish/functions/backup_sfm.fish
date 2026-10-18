function backup_sfm -d "Backup 工作量系统"
    ssh sfm "sqlite3 '/home/sid/ccx-abs-site/db.sqlite3' '.backup /home/sid/db.sqlite3'"
    rsync -a --exclude 'db.sqlite3' --exclude __pycache__ sfm:~/ccx-abs-site/ ~/cloud/Dropbox/Projects/abs_report_backup/(date +"%Y%m%d")/
    rsync -a sfm:~/db.sqlite3 ~/cloud/Dropbox/Projects/abs_report_backup/(date +"%Y%m%d")/db.sqlite3
end
