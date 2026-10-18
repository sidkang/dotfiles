function ffflv2mp4
    set input $argv[1]
    ffmpeg -i $input -c:v copy -c:a copy (basename $input .flv).mp4
end
