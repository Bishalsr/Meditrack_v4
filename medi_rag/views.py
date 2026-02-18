from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .rag import ask_rag
from .models import ChatMessage


@login_required
def chat_view(request):

    answer = None
    chat_history = ChatMessage.objects.filter(
        user=request.user
    ).order_by("-created_at")

    if request.method == "POST":
        question = request.POST.get("question")
        answer = ask_rag(question)

        # Save to DB
        ChatMessage.objects.create(
            user=request.user,
            question=question,
            answer=answer
        )

    return render(request, "medi_rag/chat.html", {
        "answer": answer,
        "chat_history": chat_history
    })
