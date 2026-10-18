function ffmute -d "Remove audio from video using ffmpeg"
    set input $argv[1]
    set output (string replace -r '\.[^.]+$' '_muted$0' $input)

    ffmpeg -i $input -an -c:v copy $output
end
