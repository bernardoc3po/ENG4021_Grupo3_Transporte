from django.db.models import Avg
from django.shortcuts import get_object_or_404, render
from UniRideSite.models import Avaliacao, Solicitacao, Trajeto


def login(request):
    '''Tela 1 - Login / Cadastro.'''
    return render(request, 'login.html')


def home(request):
    '''Tela 2 - Início: mostra o trajeto do aluno.'''
    return render(request, 'home.html')


def cadastrar_trajeto(request):
    '''Tela 3 - Cadastrar ou editar o trajeto.'''
    return render(request, 'cadastrar-trajeto.html')


def caronas_encontradas(request):
    '''Tela 4 - Lista de caronas compatíveis com o trajeto.'''
    caronas = Trajeto.objects.filter(tipo=Trajeto.OFERECE, ativo=True).annotate(
        nota=Avg('aluno__avaliacoes_recebidas__estrelas')
    )
    return render(request, 'caronas-encontradas.html', {'caronas': caronas})

def detalhes_carona(request, id):
    '''Tela 5 - Detalhes de uma carona.'''
    carona = get_object_or_404(Trajeto, id=id)
    nota = Avaliacao.objects.filter(avaliado=carona.aluno).aggregate(media=Avg('estrelas'))['media']
    total_caronas = Solicitacao.objects.filter(trajeto__aluno=carona.aluno, status=Solicitacao.ACEITA).count()
    return render(request, 'detalhes-carona.html', {'carona': carona, 'nota': nota, 'total_caronas': total_caronas})


def minhas_caronas(request):
    '''Tela 6 - Caronas do aluno (ativas e solicitações).'''
    return render(request, 'minhas-caronas.html')


def perfil(request):
    '''Tela 7 - Perfil do aluno.'''
    return render(request,'perfil.html')