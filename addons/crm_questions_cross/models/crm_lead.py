# -*- coding: utf-8 -*-
"""
Created on 2023-11-21 13:39:30

@author: drojo
"""
# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class CrmLeadInherit(models.Model):
    _inherit = 'crm.lead'
    
    ratings_ids = fields.One2many(
        'crm.ratings', 'opportunity_id', string='Calificaciones', ondelete='cascade')
    total_score = fields.Integer(
        string='Total de puntos', compute='_compute_total_score')
    key_questions_ids = fields.One2many(
        'crm.key.question.answer', 'opportunity_id')
    last_sale_date = fields.Date(
        string='Fecha de última venta', compute='_compute_last_sale_date')
    partner_vat = fields.Char(
        related='partner_id.vat')
    crm_code = fields.Char(
        string='Código', default='NEW')
    
    @api.model_create_multi
    def create(self, vals):
        for val in vals:
            if 'crm_code' not in val or val['crm_code'] == _('NEW'):
                val['crm_code'] = self.env['ir.sequence'].next_by_code('crm.lead') or _('NEW')

        return super().create(vals)

    @api.depends('ratings_ids')
    def _compute_total_score(self):
        """calculates the total points depending on the records shown in the view
        """
        for rec in self:
            rec.total_score = sum(line.score for line in rec.ratings_ids if line.show_question) if rec.ratings_ids else 0

    @api.model
    def default_get(self, default_fields):
        """default values that are loaded into the fields

        Args:
            default_fields (all): all fields

        Returns:
            dict: all fields with data
        """
        res = super(CrmLeadInherit, self). default_get(default_fields)
        questions = self.env['res.questions'].search([])

        if questions:
            add_questions = []
            stage = self.env['crm.stage'].search([], order="sequence", limit=1)
            
            for question in questions:
                if question.name:
                    add_questions.append((0,0,{
                        'question_id': question.id,
                        'answer_ref_ids': question.answer_ids,
                        'stage_ids': question.stage_ids,
                        'score': 0,
                        'show_question': True if stage in question.stage_ids else False,
                    }))
            res.update({'ratings_ids': add_questions})
        key_questions = self.env['res.key.questions'].search([])

        if key_questions:
            add_questions = []

            for question in key_questions:
                add_questions.append((0,0,{
                    'question': question.name,
                }))
            res.update({'key_questions_ids': add_questions})
        return res
    
    @api.onchange('stage_id')
    def onchange_stage_id(self):
        """dependent value change of stage_id field
        """
        for rating in self.ratings_ids:
            if self.stage_id.id in [line._origin.id for line in rating.stage_ids]:
                rating.update({'show_question': True})
            else:
                rating.update({'show_question': False})

    @api.depends('sale_amount_total', 'quotation_count')
    def _compute_last_sale_date(self):
        for rec in self:
            sale = self.env['sale.order'].search([('opportunity_id','=',rec.id)], order='id desc', limit=1)
            rec.last_sale_date = fields.Date.to_date(sale.date_order) if sale else False
    
    
class CrmRatings(models.Model):
    _name = 'crm.ratings'
    _description = 'CRM Ratings'

    opportunity_id = fields.Many2one(
        'crm.lead',string='Opportunity')
    question_id = fields.Many2one(
        'res.questions', string='Pregunta')
    name = fields.Char(
        related='question_id.name')
    answer_id = fields.Many2one(
        'res.question.answers', string='Respuesta')
    score = fields.Integer(
        related='answer_id.score')
    answer_ref_ids = fields.Many2many(
        'res.question.answers', 'ratings_id', string='Respuestas')
    stage_ids = fields.Many2many(
        'crm.stage')
    show_question = fields.Boolean(
        string='Mostrar pregunta')

    def dev_unlink(self):
        """unlink a record
        """
        self.unlink()
    

class ResQuestions(models.Model):
    _name = 'res.questions'
    _inherit = 'mail.thread'
    _description = 'Questions for ratings'

    name = fields.Char(
        string='Preguntas', tracking=True)
    answer_ids = fields.One2many(
        'res.question.answers', 'question_id', string='Respuestas', tracking=True)
    stage_ids = fields.Many2many(
        'crm.stage', string='Etapas a ser mostradas', help='Etapas del CRM en las que se mostrarán')
    answers_count = fields.Integer(
        string='Cantidad de respuestas', compute='_compute_answer_count')

    @api.model
    def create(self, values):
        """When creating a record, it also loads in the crm.lead model

        Args:
            values (all): all fields

        Returns:
            all: fields
        """
        res = super(ResQuestions, self).create(values)
        opportunity = self.env['crm.lead'].search([])
        for crm in opportunity:
            if crm.ratings_ids:
                crm.ratings_ids.create({
                    'opportunity_id': crm.id,
                    'question_id': res['id'],
                    'answer_ref_ids': res['answer_ids'],
                    'stage_ids': res['stage_ids'],
                    'score': 0,
                    'show_question': True if crm.stage_id in res['stage_ids'] else False,
                })

        return res
    
    @api.depends('answer_ids')
    def _compute_answer_count(self):
        """count the number of responses
        """
        for rec in self:
            rec.answers_count = len(rec.answer_ids)

    
class ResQuestionAnswers(models.Model):
    _name = 'res.question.answers'
    _description = 'Answers for questions'

    question_id = fields.Many2one(
        'res.questions', string='Pregunta')
    name = fields.Char(
        string='Lista de respuestas')
    score = fields.Integer(
        string='Puntuación')
    ratings_id = fields.Many2one(
        'crm.ratings',string='Calificacines')


class CrmStageInherit(models.Model):
    _inherit = 'crm.stage'

    ratings_id = fields.Many2one(
        'crm.ratings', string='Calificacines')


class ResKeyQuestions(models.Model):
    _name = 'res.key.questions'
    _description = 'Key questions for customers in CRM'

    name = fields.Char(
        string='Preguntas')


class CrmKeyQuestionAnswer(models.Model):
    _name = 'crm.key.question.answer'
    _description = 'CRM question key answer'

    opportunity_id = fields.Many2one(
        'crm.lead', string='Oportunidad')
    question = fields.Char(
        string='Pregunta')
    answer = fields.Char(
        string='Respuesta')
