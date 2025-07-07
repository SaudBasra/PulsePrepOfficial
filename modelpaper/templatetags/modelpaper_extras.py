# Create this file: modelpaper/templatetags/modelpaper_extras.py

from django import template

register = template.Library()

@register.filter
def sum_question_counts(paper_stats):
    """Calculate total questions from paper_stats list"""
    if not paper_stats:
        return 0
    
    total = 0
    for paper in paper_stats:
        if hasattr(paper, 'question_count'):
            total += paper.question_count
        elif isinstance(paper, dict) and 'question_count' in paper:
            total += paper['question_count']
    
    return total

@register.filter
def get_item(dictionary, key):
    """Get item from dictionary by key"""
    return dictionary.get(key)

@register.simple_tag
def calculate_total_questions(paper_stats):
    """Calculate total questions as a simple tag"""
    if not paper_stats:
        return 0
    
    total = 0
    for paper in paper_stats:
        if hasattr(paper, 'question_count'):
            total += paper.question_count
        elif isinstance(paper, dict) and 'question_count' in paper:
            total += paper['question_count']
    
    return total
