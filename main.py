import atexit
import csv
import random
from os.path import join
from psychopy import visual, core, event


from code.load_data import load_config
from code.screen_misc import get_screen_res
from code.show_info import part_info, show_info, show_stim, show_clock, show_timer, draw_stim_list, draw_recall_point
from code.block import prepare_block
from code.trial import Trial
from code.check_exit import check_exit


RESULTS = []
PART_ID = ""


@atexit.register
def save_beh_results():
    num = random.randint(100, 999)
    with open(join('results', '{}_beh_{}.csv'.format(PART_ID, num)), 'w', newline='') as beh_file:
        dict_writer = csv.DictWriter(beh_file, RESULTS[0].keys())
        dict_writer.writeheader()
        dict_writer.writerows(RESULTS)


def run_trial(win, trial, config, fixation, trial_clock, extra_text, clock_image, timer, show_feedback, feedback, block_type, recall_info):
    answer = None
    reaction_time = None
    acc = -1

    # fixation
    if config["fixation_time"] > 0:
        show_stim(fixation, config["fixation_time"], trial_clock, win)

    win.callOnFlip(trial_clock.reset)
    win.callOnFlip(recall_info["clock"].reset)
    win.callOnFlip(event.clearEvents)

    show_stim(trial.matrix_1, config["matrix_1_time"], trial_clock, win, recall_info)
    show_stim(trial.mask, config["mask_time"], trial_clock, win, recall_info)

    draw_stim_list(extra_text, True)
    trial_clock.reset()
    win.callOnFlip(trial_clock.reset)

    while trial_clock.getTime() < config["matrix_2_time"]:
        trial.matrix_2.draw()
        show_clock(clock_image, trial_clock, config)
        show_timer(timer, trial_clock, config)
        draw_recall_point(recall_info)

        answer = event.getKeys(keyList=config["reaction_keys"].keys())
        if answer:
            reaction_time = trial_clock.getTime()
            answer = answer[0]
            break
        check_exit()
        win.flip()

    if answer:
        acc = int(config["reaction_keys"][answer] == trial.change)

    trial_results = {"n": trial.matrix_1.n,
                     "size": [trial.matrix_1.size_y, trial.matrix_1.size_x],
                     "block_type": block_type,
                     "rt": reaction_time,
                     "acc": acc,
                     "answer": answer,
                     "correct_answer": trial.change}
    RESULTS.append(trial_results)

    draw_stim_list(extra_text, False)
    if show_feedback:
        show_stim(feedback[acc], config["fdbk_show_time"], trial_clock, win)

    wait_time = config["wait_time"] + random.random() * config["wait_jitter"]
    show_stim(None, wait_time, trial_clock, win)


def run_block(win, config, trials, stimulus_list, block_type,
              fixation, clock, extra_text, clock_image, timer, feedback, recall_info):
    for trial in trials:
        chosen_stimulus = random.sample(stimulus_list, trial["n"] + 1)
        t = Trial(win=win, config=config, n=trial["n"], change=trial["change"], size=trial["size"], group_elements=trial["group_elements"])
        t.matrix_1.prepare_to_draw(stimulus_list=chosen_stimulus[:trial["n"]], stimulus_type=config["stimulus_type"], win=win)
        t.matrix_2 = t.copy_matrix(matrix_to_copy=t.matrix_1)
        t.change_stimulus(win=win, new_stimulus=chosen_stimulus[-1], stimulus_type=config["stimulus_type"])
        run_trial(win=win, trial=t, config=config, fixation=fixation, trial_clock=clock, extra_text=extra_text, clock_image=clock_image,
                  timer=timer, feedback=feedback, show_feedback=config["fdbk_experiment"], block_type=block_type, recall_info=recall_info)


def main():
    global PART_ID
    config = load_config()
    info, PART_ID = part_info(test=config["procedure_test"])

    screen_res = dict(get_screen_res())
    win = visual.Window(list(screen_res.values()), fullscr=True, units='pix', screen=0, color=config["screen_color"])

    clock = core.Clock()
    recall_clock = core.Clock()
    fixation = visual.TextBox2(win, color=config["fixation_color"], text=config["fixation_text"],
                               letterHeight=config["fixation_size"], pos=config["fixation_pos"],
                               alignment="center")

    clock_image = visual.ImageStim(win, image=join('images', 'clock.png'), interpolate=True,
                                   size=config['clock_size'], pos=config['clock_pos'])

    timer = visual.TextBox2(win, color=config["timer_color"], text=config["matrix_2_time"],
                            letterHeight=config["timer_size"], pos=config["timer_pos"], alignment="center")

    recall_point = visual.TextBox2(win, color=config["recall_color"], text=config["recall_text"],
                                   letterHeight=config["recall_size"], alignment="center")

    recall_info = {"point": recall_point, "clock": recall_clock, "start": config["recall_time_start"], "end": config["recall_time_end"]}

    extra_text = [visual.TextBox2(win, color=text["color"], text=text["text"], letterHeight=text["size"],
                                  pos=text["pos"], alignment="center")
                  for text in config["extra_text_to_show"]]

    feedback_text = (config["fdbk_incorrect"], config["fdbk_no_answer"], config["fdbk_correct"])
    feedback = {i: visual.TextBox2(win, color=config["fdbk_color"], text=text, letterHeight=config["fdbk_size"],
                                   alignment="center")
                for (i, text) in zip([0, -1, 1], feedback_text)}

    if config["stimulus_type"] == "image":
        stimulus_list = [join("images", "all_png", elem) for elem in config["stimulus_list"]]
    elif config["stimulus_type"] == "text":
        stimulus_list = config["stimulus_list"]
    else:
        raise Exception("Unknown stimulus_type. Chose from [image, text]")

    experiment_trials = prepare_block(config["experiment_trials"], randomize=config["experiment_randomize"])

    # run training
    if config["do_training"]:
        training_trials = prepare_block(config["training_trials"], randomize=config["training_randomize"])

        show_info(win, join('.', 'messages', 'instruction_training.txt'), text_color=config["text_color"],
                  text_size=config["text_size"], screen_res=screen_res)

        run_block(win=win, config=config, trials=training_trials, stimulus_list=stimulus_list, block_type="training", fixation=fixation,
                  clock=clock, extra_text=extra_text, clock_image=clock_image, timer=timer, feedback=feedback, recall_info=recall_info)

    # run experiment
    show_info(win, join('.', 'messages', 'instruction_experiment.txt'), text_color=config["text_color"],
              text_size=config["text_size"], screen_res=screen_res)

    run_block(win=win, config=config, trials=experiment_trials, stimulus_list=stimulus_list, block_type="experiment", fixation=fixation,
              clock=clock, extra_text=extra_text, clock_image=clock_image, timer=timer, feedback=feedback, recall_info=recall_info)

    # end
    show_info(win, join('.', 'messages', 'end.txt'), text_color=config["text_color"],
              text_size=config["text_size"], screen_res=screen_res)


if __name__ == "__main__":
    main()
