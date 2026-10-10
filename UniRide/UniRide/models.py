from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

# Create your models here.
#
# Tabelas do UniRide, criadas a partir do modelo conceitual
# (Planejamento/Modelo conceitual.png), ajustado para cobrir
# os dados que as telas do protótipo já mostram:
#
#   Modelo conceitual        ->  Tabela
#   Motorista + Aluno        ->  Aluno      (a mesma pessoa pode oferecer
#                                            carona num dia e pedir no outro)
#   Veículo                  ->  Veiculo
#   Trajeto / Horário        ->  Trajeto    (oferta ou procura de carona)
#   Reserva / Leva (0..4)    ->  Solicitacao
#   Avaliação                ->  Avaliacao


class Aluno(models.Model):
    '''
    Estudante da PUC-Rio cadastrado no UniRide.
    Junta as entidades Motorista e Aluno do modelo conceitual:
    quem tem um veículo e oferece um trajeto atua como motorista,
    quem pede para entrar numa carona atua como passageiro.
    '''
    id = models.AutoField(primary_key=True)
    usuario = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='aluno',
        help_text='Usuário do Django usado no login (pode ficar vazio)',
    )
    nome = models.CharField(max_length=100, help_text='Entre o nome completo')
    email = models.EmailField(max_length=254, unique=True, help_text='E-mail institucional (@puc-rio.br)')
    matricula = models.CharField(max_length=10, unique=True, help_text='Número de matrícula na PUC-Rio')
    curso = models.CharField(max_length=100, help_text='Curso de graduação')
    membro_desde = models.DateField(help_text='Data de cadastro no UniRide', verbose_name='Membro desde')

    class Meta:
        managed = True
        db_table = 'Aluno'                  # nome da tabela
        ordering = ['nome']                 # ordenação default
        verbose_name_plural = 'Alunos'      # plural de Aluno

    def __str__(self):
        '''
        Retorna a representação em string do objeto Aluno.
        Por exemplo, o que vai ser listado na interface de admin.
        '''
        return "Aluno: " + self.nome


class Veiculo(models.Model):
    '''
    Veículo de um aluno que oferece carona.
    No modelo conceitual, cada motorista é proprietário de um veículo (1..1).
    '''
    id = models.AutoField(primary_key=True)
    motorista = models.OneToOneField(
        Aluno,
        on_delete=models.CASCADE,
        related_name='veiculo',
        help_text='Aluno proprietário do veículo',
    )
    placa = models.CharField(max_length=8, unique=True, help_text='Placa no formato ABC1D23')
    modelo = models.CharField(max_length=50, help_text='Modelo do carro (ex.: Onix)')
    cor = models.CharField(max_length=30, help_text='Cor do carro')

    class Meta:
        managed = True
        db_table = 'Veiculo'
        ordering = ['placa']
        verbose_name = 'Veículo'
        verbose_name_plural = 'Veículos'

    def __str__(self):
        '''
        Retorna a representação em string do objeto Veiculo.
        '''
        return "Veículo: " + self.modelo + " (" + self.placa + ")"


class Trajeto(models.Model):
    '''
    Trajeto cadastrado na tela "Meu trajeto".
    O aluno escolhe se quer oferecer ou procurar carona,
    a origem, os dias da semana, o horário de saída e,
    no caso de oferta, quantas vagas tem no carro.
    '''
    OFERECE = 'OFERECE'
    PROCURA = 'PROCURA'
    TIPOS = [
        (OFERECE, 'Oferece carona'),
        (PROCURA, 'Procura carona'),
    ]

    id = models.AutoField(primary_key=True)
    aluno = models.ForeignKey(
        Aluno,
        on_delete=models.CASCADE,
        related_name='trajetos',
        help_text='Aluno dono do trajeto',
    )
    tipo = models.CharField(max_length=7, choices=TIPOS, help_text='Oferece ou procura carona')
    origem = models.CharField(max_length=100, help_text='Bairro de partida (ex.: Botafogo)')
    destino = models.CharField(max_length=100, default='PUC-Rio', help_text='Destino da carona')
    horario = models.TimeField(help_text='Horário de saída no formato HH:MM', verbose_name='Horário de saída')
    vagas = models.PositiveSmallIntegerField(
        default=0,
        validators=[MaxValueValidator(4)],
        help_text='Vagas oferecidas no carro (1 a 4). Use 0 quando o aluno procura carona.',
    )
    # Dias da semana em que o trajeto acontece
    dom = models.BooleanField(default=False, verbose_name='Domingo')
    seg = models.BooleanField(default=False, verbose_name='Segunda')
    ter = models.BooleanField(default=False, verbose_name='Terça')
    qua = models.BooleanField(default=False, verbose_name='Quarta')
    qui = models.BooleanField(default=False, verbose_name='Quinta')
    sex = models.BooleanField(default=False, verbose_name='Sexta')
    sab = models.BooleanField(default=False, verbose_name='Sábado')
    ativo = models.BooleanField(default=True, help_text='Desmarque para esconder o trajeto da busca')

    class Meta:
        managed = True
        db_table = 'Trajeto'
        ordering = ['horario']
        verbose_name_plural = 'Trajetos'

    def dias_da_semana(self):
        '''
        Retorna a lista com as abreviações dos dias marcados.
        Por exemplo: ['Seg', 'Qua', 'Sex'].
        Útil para montar os "chips" de dias nas telas.
        '''
        dias = [
            ('Dom', self.dom), ('Seg', self.seg), ('Ter', self.ter), ('Qua', self.qua),
            ('Qui', self.qui), ('Sex', self.sex), ('Sáb', self.sab),
        ]
        return [nome for nome, marcado in dias if marcado]

    def __str__(self):
        '''
        Retorna a representação em string do objeto Trajeto.
        '''
        return "Trajeto: " + self.origem + " → " + self.destino + " (" + self.aluno.nome + ")"


class Solicitacao(models.Model):
    '''
    Pedido de um passageiro para entrar no trajeto oferecido por um motorista.
    Representa a relação "Reserva" do modelo conceitual.
    Quando o motorista aceita, a carona passa a acontecer ("Match confirmado!").
    '''
    PENDENTE = 'PENDENTE'
    ACEITA = 'ACEITA'
    RECUSADA = 'RECUSADA'
    STATUS = [
        (PENDENTE, 'Aguardando confirmação'),
        (ACEITA, 'Aceita'),
        (RECUSADA, 'Recusada'),
    ]

    id = models.AutoField(primary_key=True)
    trajeto = models.ForeignKey(
        Trajeto,
        on_delete=models.CASCADE,
        related_name='solicitacoes',
        help_text='Trajeto oferecido pelo motorista',
    )
    passageiro = models.ForeignKey(
        Aluno,
        on_delete=models.CASCADE,
        related_name='solicitacoes',
        help_text='Aluno que pediu a carona',
    )
    status = models.CharField(max_length=8, choices=STATUS, default=PENDENTE, help_text='Situação do pedido')
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name='Data do pedido')

    class Meta:
        managed = True
        db_table = 'Solicitacao'
        ordering = ['-data_criacao']
        verbose_name = 'Solicitação'
        verbose_name_plural = 'Solicitações'
        constraints = [
            # Um aluno só pode pedir uma vez para entrar no mesmo trajeto
            models.UniqueConstraint(fields=['trajeto', 'passageiro'], name='solicitacao_unica_por_trajeto'),
        ]

    def __str__(self):
        '''
        Retorna a representação em string do objeto Solicitacao.
        '''
        return "Solicitação: " + self.passageiro.nome + " → carona de " + self.trajeto.aluno.nome


class Avaliacao(models.Model):
    '''
    Nota de 1 a 5 estrelas e comentário dados depois de uma carona.
    Motorista e passageiro podem se avaliar mutuamente,
    e cada um avalia no máximo uma vez por carona (0..1 no modelo conceitual).
    '''
    id = models.AutoField(primary_key=True)
    solicitacao = models.ForeignKey(
        Solicitacao,
        on_delete=models.CASCADE,
        related_name='avaliacoes',
        help_text='Carona (solicitação aceita) que está sendo avaliada',
    )
    avaliador = models.ForeignKey(
        Aluno,
        on_delete=models.CASCADE,
        related_name='avaliacoes_feitas',
        help_text='Aluno que fez a avaliação',
    )
    avaliado = models.ForeignKey(
        Aluno,
        on_delete=models.CASCADE,
        related_name='avaliacoes_recebidas',
        help_text='Aluno que recebeu a avaliação',
    )
    estrelas = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text='Nota de 1 a 5',
    )
    comentario = models.TextField(blank=True, help_text='Comentário opcional', verbose_name='Comentário')
    data = models.DateTimeField(auto_now_add=True, verbose_name='Data da avaliação')

    class Meta:
        managed = True
        db_table = 'Avaliacao'
        ordering = ['-data']
        verbose_name = 'Avaliação'
        verbose_name_plural = 'Avaliações'
        constraints = [
            # Cada aluno avalia no máximo uma vez a mesma carona
            models.UniqueConstraint(fields=['solicitacao', 'avaliador'], name='avaliacao_unica_por_carona'),
        ]

    def __str__(self):
        '''
        Retorna a representação em string do objeto Avaliacao.
        '''
        return "Avaliação: " + self.avaliador.nome + " → " + self.avaliado.nome + " (" + str(self.estrelas) + "★)"
