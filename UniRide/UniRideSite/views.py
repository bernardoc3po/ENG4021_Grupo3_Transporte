from django.contrib.auth import authenticate, login as entrar, logout as deslogar
from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from UniRideSite.models import Aluno, Avaliacao, Solicitacao, Trajeto


def aluno_temporario(request):
    return get_object_or_404(Aluno, user=request.user)

def login(request):
    '''Tela 1 - Login: confere e-mail e senha e abre a sessão do aluno.'''
    erro = None
    if request.method == 'POST':
        user = authenticate(request, username=request.POST['email'], password=request.POST['senha'])
        if user is not None:
            entrar(request, user)
            return redirect('home')
        erro = 'E-mail ou senha incorretos.'
    return render(request, 'login.html', {'erro': erro})


def sair(request):
    '''Encerra a sessão e volta para o login.'''
    deslogar(request)
    return redirect('login')


@login_required
def home(request):
    '''Tela 2 - Início: mostra o trajeto do aluno.'''
    return render(request, 'home.html')


@login_required
def cadastrar_trajeto(request):
    '''Tela 3 - Cadastrar um trajeto.'''
    if request.method == 'POST':
        aluno = aluno_temporario(request)
        dias = request.POST.getlist('dias')
        Trajeto.objects.create(
            aluno=aluno,
            tipo=request.POST.get('tipo'),
            origem=request.POST.get('origem'),
            destino=request.POST.get('destino'),
            horario=request.POST.get('horario'),
            vagas=int(request.POST.get('vagas', 0)),
            dom='dom' in dias,
            seg='seg' in dias,
            ter='ter' in dias,
            qua='qua' in dias,
            qui='qui' in dias,
            sex='sex' in dias,
            sab='sab' in dias
        )
        return redirect('home')
    return render(request, 'cadastrar-trajeto.html')


def caronas_encontradas(request):
    '''Tela 4 - Busca de caronas.'''
    caronas = Trajeto.objects.filter(tipo=Trajeto.OFERECE, ativo=True).annotate(nota=Avg('aluno__avaliacoes_recebidas__estrelas'))
    origem = request.GET.get('origem')
    horario = request.GET.get('horario')
    dia = request.GET.get('dia')
    if origem:
        caronas = caronas.filter(origem__icontains=origem)
    if horario:
        caronas = caronas.filter(horario=horario)
    if dia in ['dom', 'seg', 'ter', 'qua', 'qui', 'sex', 'sab']:
        caronas = caronas.filter(**{dia: True})
    return render(request, 'caronas-encontradas.html', {'caronas': caronas,'origem': origem,'horario': horario,'dia': dia})

@login_required
def detalhes_carona(request, id):
    '''Tela 5 - Detalhes de uma carona.'''
    carona = get_object_or_404(Trajeto, id=id)
    nota = Avaliacao.objects.filter(avaliado=carona.aluno).aggregate(media=Avg('estrelas'))['media']
    total_caronas = Solicitacao.objects.filter(trajeto__aluno=carona.aluno, status=Solicitacao.ACEITA).count()
    return render(request, 'detalhes-carona.html', {'carona': carona, 'nota': nota, 'total_caronas': total_caronas})


@login_required
def minhas_caronas(request):
    '''Tela 6 - Caronas do aluno (ativas e solicitações).'''
    aluno = aluno_temporario(request)

    # Pedidos que o aluno fez como passageiro (já traz o motorista junto)
    pedidos = aluno.solicitacoes.select_related('trajeto__aluno')

    contexto = {
        'aluno': aluno,
        'caronas_aceitas': pedidos.filter(status=Solicitacao.ACEITA),
        'pedidos_pendentes': pedidos.filter(status=Solicitacao.PENDENTE),
        'pedidos_recusados': pedidos.filter(status=Solicitacao.RECUSADA),
    }

        # Se o aluno oferece carona, busca os pedidos recebidos no trajeto dele
    trajeto_motorista = aluno.trajetos.filter(tipo=Trajeto.OFERECE, ativo=True).first()
    if trajeto_motorista:
        recebidos = trajeto_motorista.solicitacoes.select_related('passageiro')
        contexto['trajeto_motorista'] = trajeto_motorista
        contexto['pedidos_recebidos'] = recebidos.filter(status=Solicitacao.PENDENTE)
        contexto['passageiros_confirmados'] = recebidos.filter(status=Solicitacao.ACEITA)
   
    return render(request, 'minhas-caronas.html', contexto)


@login_required
def perfil(request):
    '''Tela 7 - Perfil do aluno.'''
    return render(request,'perfil.html')

@login_required
def editar_perfil(request):
    '''Tela 7.1 - Editar perfil: salva nome e curso do aluno.'''
    aluno = aluno_temporario(request)
    if request.method == 'POST':
        aluno.nome = request.POST['nome']
        aluno.curso = request.POST['curso']
        aluno.save()
        return redirect('perfil')
    trajeto = aluno.trajetos.first()
    return render(request, 'editar-perfil.html', {'aluno': aluno, 'trajeto': trajeto})

@login_required
def solicitar_carona(request, id):
    '''Cria um pedido de carona (PENDENTE) para o trajeto escolhido.'''
    carona = get_object_or_404(Trajeto, id=id)
    if request.method == 'POST':
        passageiro = aluno_temporario(request)
        Solicitacao.objects.get_or_create(trajeto=carona, passageiro=passageiro)
    return redirect(reverse('detalhes-carona', args=[id]) + '#enviado')