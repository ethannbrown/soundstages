import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

from config import FIGURES, RESULTS

ERAS = ['Acoustic', 'Electric', 'Loudness war', 'Streaming']
ERA_YEARS = ['to 1973', '1974–98', '1999–2016', '2017+']
QUANTILES = [0.25, 0.5, 0.9]

INK = '#2b2b29'
MUTED = '#6f6e69'
GRID = '#e6e5e0'
SURFACE = '#fcfcfb'
BLUE, ORANGE = '#2a78d6', '#eb6834'
ERA_COLORS = ['#6da7ec', '#2a78d6', '#184f95', '#0d366b']
FEATURE_COLORS = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300']

plt.rcParams.update({
    'font.size': 11,
    'axes.edgecolor': GRID,
    'axes.labelcolor': MUTED,
    'xtick.color': MUTED,
    'ytick.color': MUTED,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'figure.facecolor': SURFACE,
    'axes.facecolor': SURFACE,
    'savefig.facecolor': SURFACE,
})
FIGURES.mkdir(parents=True, exist_ok=True)

# r1 per subset, quantile and fold, with the gain from adding sound
scores = pd.read_csv(RESULTS / 'boost_scores.csv')
r1 = scores.pivot_table(index=['subset', 'quantile', 'fold'], columns='model', values='r1')
r1['gain'] = r1['audio'] - r1['background']
summary = r1.groupby(['subset', 'quantile']).agg(
    background=('background', 'mean'), gain=('gain', 'mean'), gain_sd=('gain', 'std')
) * 100
print(f'Loaded XGBoost scores for {scores["subset"].nunique()} subsets')

# Figure 1: who made it vs how it sounds, median track, by era
median = summary.xs(0.5, level='quantile').loc[ERAS]
fig, ax = plt.subplots(figsize=(8, 4.8))
x = range(len(ERAS))
ax.bar(x, median['background'], width=0.6, color=BLUE, label='Who made it (artist reach, genre, year, length)')
ax.bar(x, median['gain'], width=0.6, bottom=median['background'] + 0.3, color=ORANGE,
       label='How it sounds (10 audio features)')
for i, era in enumerate(ERAS):
    share = median.loc[era, 'gain'] / median.loc[era, 'background']
    top = median.loc[era, 'background'] + median.loc[era, 'gain']
    ax.text(i, top + 0.8, f'sound = {share:.0%}\nof who made it', ha='center', va='bottom', color=INK, fontsize=9.5)
ax.set_xticks(list(x), [f'{e}\n{y}' for e, y in zip(ERAS, ERA_YEARS, strict=True)])
ax.set_ylabel('Share of popularity explained (%)')
ax.set_ylim(0, 40)
ax.yaxis.grid(True, color=GRID)
ax.set_axisbelow(True)
ax.legend(frameon=False, loc='upper left', fontsize=9.5, labelcolor=INK)
ax.set_title('Sound adds about the same in every era. Who made the song keeps growing.', loc='left', color=INK,
             fontsize=12)
fig.tight_layout()
fig.savefig(FIGURES / 'who_vs_sound.png', dpi=200)
plt.close(fig)
print('Saved who_vs_sound.png')

# Figure 2: sound's gain at each point of the distribution, by era
fig, ax = plt.subplots(figsize=(8, 4.8))
# Small sideways offsets so the error bars don't sit on top of each other
for i, (era, color) in enumerate(zip(ERAS, ERA_COLORS, strict=True)):
    rows = summary.loc[era].loc[QUANTILES]
    xs = [q + (i - 1.5) * 0.06 for q in range(len(QUANTILES))]
    ax.errorbar(xs, rows['gain'], yerr=rows['gain_sd'], color=color, lw=2, marker='o', ms=8, capsize=3, label=era)
labels = ['Lower tracks\n(25th percentile)', 'Typical tracks\n(median)', 'Near the top\n(90th percentile)']
ax.set_xticks(range(len(QUANTILES)), labels)
ax.set_xlim(-0.3, len(QUANTILES) - 0.3)
ax.set_ylabel('Extra share explained by sound (points)')
ax.set_ylim(0, 7)
ax.yaxis.grid(True, color=GRID)
ax.set_axisbelow(True)
ax.legend(frameon=False, loc='upper left', fontsize=9.5, labelcolor=INK, ncol=4)
ax.set_title('Sound helps most for typical tracks and least near the top', loc='left', color=INK, fontsize=12)
fig.tight_layout()
fig.savefig(FIGURES / 'sound_by_percentile.png', dpi=200)
plt.close(fig)
print('Saved sound_by_percentile.png')

# Figure 3: which sounds matter near the top, by era
# SHAP difference between tracks above and below each feature's median, in popularity points
shap = pd.read_csv(RESULTS / 'boost_shap.csv')
shap['effect'] = shap['mean_high'] - shap['mean_low']
features = {
    'loudness': 'Louder',
    'log_duration': 'Longer',
    'valence': 'Happier',
    'danceability': 'More danceable',
    'acousticness': 'More acoustic',
    'liveness': 'More live-sounding',
}
top = shap[shap['quantile'] == 0.9].groupby(['feature', 'subset'])['effect'].mean().unstack().loc[list(features), ERAS]
# End labels that would overlap get moved up or down a little
nudge = {'log_duration': 0.12, 'liveness': -0.12}
fig, ax = plt.subplots(figsize=(8, 5.2))
ax.axhline(0, color=MUTED, lw=1)
for (feature, label), color in zip(features.items(), FEATURE_COLORS, strict=True):
    ax.plot(range(len(ERAS)), top.loc[feature], color=color, lw=2, marker='o', ms=8, label=label)
    ax.text(len(ERAS) - 1 + 0.08, top.loc[feature].iloc[-1] + nudge.get(feature, 0), label, color=INK, va='center',
            fontsize=9.5)
ax.set_xticks(range(len(ERAS)), [f'{e}\n{y}' for e, y in zip(ERAS, ERA_YEARS, strict=True)])
ax.set_xlim(-0.3, len(ERAS) + 0.4)
ax.set_ylabel('Popularity points, near the top\n(above vs below the feature median)')
ax.yaxis.grid(True, color=GRID)
ax.set_axisbelow(True)
ax.legend(frameon=False, loc='upper left', fontsize=9, labelcolor=INK, ncol=3)
ax.set_title('Some rules held, others flipped', loc='left', color=INK, fontsize=12)
fig.tight_layout()
fig.savefig(FIGURES / 'which_sounds.png', dpi=200)
plt.close(fig)
print('Saved which_sounds.png')
