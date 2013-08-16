from django.http import Http404, HttpResponse
from django.core.urlresolvers import reverse
from django.shortcuts import render, get_object_or_404

from analyzer.word_splitter import analyze_word
from analyzer.describers import describe_word
from morphology.models import *

def index(request):
	data = {}
	if 'sentence' in request.POST:
		sentence = request.POST['sentence']
		words = sentence.split()
		data['result'] = []
		for word in words:
			slots = analyze_word(word)
			if 'error' in slots:
				return render(request, 'analyzer/index_error.html', slots)
			desc = {'word': word}
			desc.update(describe_word(slots))
			if 'error' in desc:
				return render(request, 'analyzer/index_error.html', desc)
			data['result'].append(desc)
					
		return render(request, 'analyzer/index_display.html', data)
	else:
		return render(request, 'analyzer/index_form.html', data)
		