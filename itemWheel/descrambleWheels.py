import numpy as np
import matplotlib.pyplot as plt

from matplotlib.colors import ListedColormap

NUM_WHEELS = 3
ITEM_DICT = {0x00: 'Bomb',
             0x01: 'Fireball',
             0x02: 'Missile',
             0x03: 'Turbo',
             0x04: 'Jump',
             0x05: 'Crazy Mushroom',
             0x06: 'Stealth Field',
             0x07: 'Big, Bigger, Biggest!',
             0x08: 'Tiny, Tiny, Tiny!',
             0x09: 'Oil Slick',
             0x0A: 'Pandora\'s Box',
             0x0B: 'Dynamite',
             0x0C: 'Super Shield',
             0x0D: '2 Player Only (0x0D)',
             0x0E: 'Wonder Clock',
             0x0F: '32t Weight',
             0x10: 'Power Up',
             0x11: '2 Player Only (0x11)'}

# Slightly hacky globals that allow for pretty printing
# This allows for a mostly functional-style implementation without having to pass these around
REDIRECTS = None
WHEELS = None

def parseItemWheels(wheel_file='itemWheel.dmp'):
    """
    Reads the provided file where each line is assumed to be a wheel.
    Each wheel is then parsed and stored into a list (the return value)

    :param wheel_file: The file to be parsed
    :return: A list of item wheels in file provided order
    """
    item_wheels = []

    with open(wheel_file, 'r') as wheels:
        for wheel in wheels:
            a_wheel = []

            for item in wheel.split(','):
                item = item.strip()
                a_wheel.append(item)

            item_wheels.append(a_wheel)

    return item_wheels

def parseWheelRedirects(redirect_file='wheelindexRedirect.dmp'):
    """
    Reads the provided file where each line is a single number (in hex) which represents the index of an item wheel

    :param redirect_file: The file to be parsed
    """
    wheel_redirects = []

    with open(redirect_file, 'r') as redirects:
        for redirect in redirects:
            wheel_redirects.append(int(redirect.strip(), 16))

    return wheel_redirects

# wheelIndexLookup = &DAT_800e4498 + (lapCountBase0 * 2 + (uint)pd->halfway) * 0x1e + racePosB1 * 3;
def getWheelStartIndex(lap_count, halfway, race_pos):
    """
    Returns the starting index (location in the wheel lookup table) based on player state.

    :param lap_count: Number of laps | Count in base 0
    :param halfway: Bool - are you halfway around the track?
    :param race_pos: Current race position | Count in base 1 (e.g. 1-9 inclusive)
    """
    return ((lap_count * 2) + (1 if halfway else 0)) * 0x1e + (race_pos * 3)

def ppWheel(lookup_index):
    """
    Pretty printing of an item wheel to the console

    :param lookup_index: The index of the wheel to be printed
    """
    wheel_index = REDIRECTS[lookup_index]
    wheel = WHEELS[wheel_index]
    print(f'-----------------------\n'
          f'lookupIdx:   {lookup_index}\n'
          f'wheelOffset: {wheel_index}\n'
          f'StartAddr:   {hex(0x8008d0c0 + (REDIRECTS[lookup_index] * 8))}\n'
          f'-----------------------')
    print(f'Wheel: {wheel}')

    for item_idx in wheel:
        print('   ', ITEM_DICT[int(item_idx, 16)])
    print('\n')


def wheelsLookup(lap_count, halfway, race_pos, no_print=False):
    """
    Converts a players race status into a dictionary of possible item encounters

    :param lap_count: Number of laps | Count in base 0
    :param halfway: Bool - are you halfway around the track?
    :param race_pos: Current race position | Count in base 1 (e.g. 1-9 inclusive)
    :return: A dictionary where:
        Key: item ID
        Value: number of wheels the item is present in (out of 3 max possible)
    """
    lookup_start_index = getWheelStartIndex(lap_count, halfway, race_pos)
    if not no_print:
        print(f'\n\n--------------------------------------------------------------------------------')
    if not no_print:
        print(f'Lap:       {lap_count + 1}\n'
            f'Halfway:   {halfway}\n'
            f'Position:  {race_pos}\n'
            f'-----------------------\n')

    if not no_print:
        print(f'lookup start index: {lookup_start_index}')
    wheels = []
    lookup_index = lookup_start_index
    for _ in range(NUM_WHEELS):
        if not no_print:
            ppWheel(lookup_index)
        wheel_index = REDIRECTS[lookup_index]
        wheels.append(WHEELS[wheel_index])
        lookup_index = lookup_index + 1

    item_info = {}
    for wheel in wheels:
        item_temp = {}
        for hex_item in wheel:
            item = int(hex_item, 16)
            if item not in item_info:
                item_info[item] = 0
            if item not in item_temp:
                item_temp[item] = True
                item_info[item] = item_info[item] + 1

    stats_strings = []
    for item_id in ITEM_DICT.keys():
        name = ITEM_DICT[item_id]

        if '2 Player' in name:
            continue # skip 2 Player only items

        count = item_info.get(item_id, 0)
        stats_strings.append(f'| {name:<21} | {(f"{count / float(NUM_WHEELS) * 100:.2f}"):>6} % |')

    if not no_print:
        stats_strings.sort()
        for stat in stats_strings:
            print(f'+-----------------------+----------+')
            print(stat)
        print(f'+----------------------------------+')
        print(f'--------------------------------------------------------------------------------')

    print(item_info)
    return item_info

def generate_graph(stats, item, save_graph=True, show_graph=False):
    """
    Generates a heatmap of the item encounter rate chance for a range of race and lap positions.
    Can be optionally displayed or saved that.

    :param stats: Dictionary of item encounter rates
        Key: tuple of (race_prog, race_pos, item)
        Value: Number of wheels (max 3) that contain this item given the player state (defined by the key)
    :param item: Item ID for which the graph will be generated
    :param save_graph: If True, graph will be saved to a "graphs" directory in the cwd
    :param show_graph: If True, will display graph to user
    """
    graph_data = np.zeros(shape=(10,6), dtype=float)
    for race_prog_int in range(6):
        for race_pos in range(0, 10):
            race_prog = race_prog_int / 2.0
            item_chance = stats.get((race_prog, race_pos, item), 0.0) / float(NUM_WHEELS)
            graph_data[race_pos][race_prog_int] = np.float64(item_chance)

    # discrete color scheme
    ctf = 255.0 # color int to float
    sat = 230
    yes=tuple(np.array([18, 39, 64, sat]) / ctf)
    high=tuple(np.array([50, 107, 119, sat]) / ctf)
    low=tuple(np.array([132, 178, 158, sat]) / ctf)
    no=tuple(np.array([244, 246, 204, sat]) / ctf)
    c_map = ListedColormap([no, low, high, yes])

    plt.rcParams.update({'font.size': 22}) # font size
    fig, ax = plt.subplots()
    heatmap = ax.pcolor(graph_data, cmap=c_map, vmin=0, vmax=1)

    # legend
    cbar = plt.colorbar(heatmap)

    cbar.ax.get_yaxis().set_ticks([])
    for j, lab in enumerate(['$0\%$','$33.3\%$','$66.6\%$','$100\%$']):
        cbar.ax.text(1.1, (2 * j + 1) / 8.0, lab, ha='left', va='center')

    # Turn spines off and create black (major) grid with border
    ax.grid(which='major', color="black", linestyle='-', linewidth=2)
    ax.set_xticks(np.arange(graph_data.shape[1]), np.arange(graph_data.shape[1]))
    ax.set_yticks(np.arange(graph_data.shape[0]), np.arange(graph_data.shape[0]))
    ax.patch.set_edgecolor('black')
    ax.patch.set_linewidth('2')

    # hacky way to remove minor major ticks
    ax.tick_params(axis='both', which='major', colors='white')

    # put the major ticks at the middle of each cell
    ax.set_xticks(np.arange(graph_data.shape[1]) + 0.5, np.arange(graph_data.shape[1]), minor=True)
    ax.set_yticks(np.arange(graph_data.shape[0]) + 0.5, np.arange(graph_data.shape[0]), minor=True)
    ax.invert_yaxis()

    # Update lables to be the correct base and format
    ax.set_xticklabels(np.arange(1, 4, 0.5, dtype=float), minor=True)
    ax.set_yticklabels(np.arange(0, 10), minor=True)

    # Generate title and filename
    item_name = ITEM_DICT[item]
    title = f'{item_name} - Item Encounter Rate'
    plt.rcParams['axes.titley'] = 1.025 # shift title up juuuust a bit
    filename = title.replace('-', '').replace(' ', '_')
    plt.title(title)
    plt.xlabel("Lap")
    plt.ylabel("Race Position", )

    # set file size and save
    fig.set_size_inches(18.5, 10.5)
    if save_graph:
        plt.savefig(f'./graphs/{filename}.png')

    if show_graph:
        plt.show()


def main():
    global REDIRECTS
    global WHEELS
    REDIRECTS = parseWheelRedirects()
    WHEELS = parseItemWheels()

    raw_stats = {}
    for lap_count in range(3):
        for halfway_toggle in range(2):
            halfway = True if halfway_toggle >= 1 else False
            for race_pos in range(10):
                stats = wheelsLookup(lap_count=lap_count, halfway=halfway, race_pos=race_pos, no_print=False)
                for item, count in stats.items():
                    race_prog = lap_count + (0.5 if halfway else 0.0)
                    raw_stats[(race_prog, race_pos, item)] = count

    for item_id, item_name in ITEM_DICT.items():
        if '2 Player' in item_name:
            continue # skip 2 Player only items
        generate_graph(raw_stats, item_id, show_graph=True, save_graph=False)

if __name__ == "__main__":
    main()