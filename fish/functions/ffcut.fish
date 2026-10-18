function ffcut -d "Cut video using ffmpeg with start time and optional duration"
    set input $argv[1]
    set start $argv[2]
    # argv[3] stop
    set output (string replace -r '\.[^.]+$' '_cut$0' $input)

    if test (count $argv) -eq 3
        ffmpeg -i $input -ss $start -to $argv[3] -c:v libx264 -c:a aac $output
    else
        ffmpeg -i $input -ss $start -c:v libx264 -c:a aac $output
    end
end
