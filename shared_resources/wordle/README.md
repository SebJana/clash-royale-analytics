# Wordle Word Lists

This directory contains the official Wordle word lists used for game logic and validation.

## Files

### `possible-solutions.txt`

Contains all 2,309 possible solution words that can appear as the answer in Wordle puzzles. These are the words that the New York Times uses as valid solutions.

**Purpose**:

- Used for generating random Wordle answers
- Represents the official answer pool
- These are common, recognizable English words

**Format**: One word per line, all lowercase, 5 letters each

### `valid-guesses.txt`

Contains the complete list of valid guesses (~12,972 words) that Wordle accepts as input during gameplay. This includes both the possible solutions plus additional valid English words.

**Purpose**:

- Used for validating user input
- Ensures only legitimate English words are accepted
- Includes obscure but valid words that won't be answers

**Format**: One word per line, all lowercase, 5 letters each

**Note**: This file includes all words from `possible-solutions.txt` plus approximately 10,663 additional valid words that can be guessed but will never be the answer.

## Data Sources

### Valid Guesses

The complete list of valid guesses (accepted input words) can be found here:

- **Source**: [GitHub Gist by kcwhite](https://gist.github.com/kcwhite/bb598f1b3017b5477cb818c9b086a5d9)
- **Contains**: ~12,000+ words that Wordle accepts as valid guesses

### Possible Solution Words

The curated list of possible answer words comes from:

- **Primary Source**: [Word Raiders Word Finder](https://wordraiders.com/wordfinder-results/)
- **Secondary Source**: [GitHub Gist by cfreshman](https://gist.github.com/cfreshman/a03ef2cba789d8cf00c08f767e0fad7b?utm_source=chatgpt.com)
- **Contains**: 2,309 words that can appear as Wordle solutions

## Usage

The word lists are used by the application's Wordle functionality to:

- **Generate random Wordle answers** using `possible-solutions.txt`
- **Validate user guesses** using `valid-guesses.txt`
- **Ensure game consistency** with official Wordle rules
- **Separate answer pool from guess pool** to maintain game balance

### Implementation Notes

- Solutions are drawn only from the smaller, curated list of common words
- All guesses are validated against the larger comprehensive word list
- This mirrors the official NYT Wordle game mechanics exactly
