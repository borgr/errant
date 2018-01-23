import argparse
import os
import sys
import spacy
from nltk.stem.lancaster import LancasterStemmer
import errant.scripts.align_text as align_text
import errant.scripts.cat_rules as cat_rules
import errant.scripts.toolbox as toolbox
import six

resources = {}

def main(args):
	resources = init_resources()
	nlp = resources["nlp"]
	stemmer = resources["stemmer"]
	gb_spell = resources["gb_spell"]
	tag_map = resources["tag_map"]
	# Setup output m2 file
	out_m2 = open(args.out, "w")

	print("Processing files...")
	# Open the original and corrected text files.
	with open(args.orig) as orig, open(args.cor) as cor:
		# Process each pre-aligned sentence pair.
		for orig_sent, cor_sent in zip(orig, cor):
			# Write the original sentence to the output m2 file.
			out_m2.write("S "+orig_sent)
			# Identical sentences have no edits, so just write noop.
			if orig_sent.strip() == cor_sent.strip():
				out_m2.write("A -1 -1|||noop|||-NONE-|||REQUIRED|||-NONE-|||0\n")
			# Otherwise, do extra processing.
			else:
				# Markup the parallel sentences with spacy (assume tokenized)
				proc_orig = toolbox.applySpacy(orig_sent.strip().split(), nlp)
				proc_cor = toolbox.applySpacy(cor_sent.strip().split(), nlp)
				# Auto align the parallel sentences and extract the edits.
				auto_edits = align_text.getAutoAlignedEdits(proc_orig, proc_cor, nlp, args.lev, args.merge)
				# Loop through the edits.
				for auto_edit in auto_edits:
					# Give each edit an automatic error type.
					cat = cat_rules.autoTypeEdit(auto_edit, proc_orig, proc_cor, gb_spell, tag_map, nlp, stemmer)
					auto_edit[2] = cat
					# Write the edit to the output m2 file.
					out_m2.write(toolbox.formatEdit(auto_edit)+"\n")
			# Write a newline when there are no more edits.
			out_m2.write("\n")
	out_m2.close()

def init_resources():
	if resources == {}:
		# Get base working directory.
		basename = os.path.dirname(os.path.realpath(__file__))
		print("Loading errant resources...")
		# Load Tokenizer and other resources
		resources["nlp"] = spacy.load("en")
		# Lancaster Stemmer
		resources["stemmer"] = LancasterStemmer()
		# GB English word list (inc -ise and -ize)
		resources["gb_spell"] = toolbox.loadDictionary(basename+"/resources/en_GB-large.txt")
		# Part of speech map file
		resources["tag_map"] = toolbox.loadTagMap(basename+"/resources/en-ptb_map")
	return resources

def parallel_to_m2(orig_sents, cor_sents, lev=False, merge="rules"):
	resources = init_resources()
	nlp = resources["nlp"]
	stemmer = resources["stemmer"]
	gb_spell = resources["gb_spell"]
	tag_map = resources["tag_map"]
	out_m2 = []

	print("Processing...")
	# Change format if got a list of reference per original and not a list of lists of references
	if isinstance(cor_sents[0], six.string_types):
		cor_sents = [[cor_sent] for cor_sent in cor_sents]
	# Process each pre-aligned sentence pair.
	for orig_sent, cor_sents in zip(orig_sents, cor_sents):
		# Write the original sentence to the output m2 file.
		out_m2.append("S " + orig_sent)
		for coder_id, cor_sent in enumerate(cor_sents):
			# Identical sentences have no edits, so just write noop.
			if orig_sent.strip() == cor_sent.strip():
				out_m2.append("A -1 -1|||noop|||-NONE-|||REQUIRED|||-NONE-|||" + str(coder_id) + "\n")
			# Otherwise, do extra processing.
			else:
				# Markup the parallel sentences with spacy (assume tokenized)
				proc_orig = toolbox.applySpacy(orig_sent.strip().split(), nlp)
				proc_cor = toolbox.applySpacy(cor_sent.strip().split(), nlp)
				# Auto align the parallel sentences and extract the edits.
				auto_edits = align_text.getAutoAlignedEdits(proc_orig, proc_cor, nlp, lev, merge)
				# Loop through the edits.
				for auto_edit in auto_edits:
					# Give each edit an automatic error type.
					cat = cat_rules.autoTypeEdit(auto_edit, proc_orig, proc_cor, gb_spell, tag_map, nlp, stemmer)
					auto_edit[2] = cat
					# Write the edit to the output m2 file.
					out_m2.append(toolbox.formatEdit(auto_edit, coder_id=coder_id)+"\n")
			# Write a newline when there are no more edits.
	return out_m2
			
if __name__ == "__main__":
	# Define and parse program input
	parser = argparse.ArgumentParser(description="Convert parallel original and corrected text files (1 sentence per line) into M2 format.\nThe default uses Damerau-Levenshtein and merging rules and assumes tokenized text.",
								formatter_class=argparse.RawTextHelpFormatter,
								usage="%(prog)s [-h] [options] -orig ORIG -cor COR -out OUT")
	parser.add_argument("-orig", help="The path to the original text file.", required=True)
	parser.add_argument("-cor", help="The path to the corrected text file.", required=True)
	parser.add_argument("-out",	help="The output filepath.", required=True)						
	parser.add_argument("-lev",	help="Use standard Levenshtein to align sentences.", action="store_true")
	parser.add_argument("-merge", choices=["rules", "all-split", "all-merge", "all-equal"], default="rules",
						help="Choose a merging strategy for automatic alignment.\n"
								"rules: Use a rule-based merging strategy (default)\n"
								"all-split: Merge nothing; e.g. MSSDI -> M, S, S, D, I\n"
								"all-merge: Merge adjacent non-matches; e.g. MSSDI -> M, SSDI\n"
								"all-equal: Merge adjacent same-type non-matches; e.g. MSSDI -> M, SS, D, I")
	args = parser.parse_args()
	# Run the program.
	main(args)
