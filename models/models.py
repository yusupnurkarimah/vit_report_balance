# -*- coding: utf-8 -*-

from odoo import models, fields, api
import time
import logging
from io import BytesIO
import xlsxwriter
import base64
from datetime import datetime
from odoo.exceptions import Warning
import base64

_logger = logging.getLogger(__name__)

class report_balance(models.Model):
	_name = 'vit.report_balance'

	name = fields.Char(string='No',required=True, size=100)
	date_start = fields.Date(string='Date Start', required=False,
						default=lambda self:time.strftime("%Y-%m-%d"))
	date_end = fields.Date(string='Date End', required=False,
						default=lambda self:time.strftime("%Y-%m-%d"))
	name_report = fields.Selection(
		string='Report Name',
		selection=[('Report Balance SO', 'Report Balance SO'), ('Report Balance WIP', 'Report Balance WIP')], 
		required=True,readonly=True)
	company_id = fields.Many2one(comodel_name='res.company', string='Company')
	report_so_ids = fields.One2many('vit.report_balance_so','report_id',string='Report')
	report_wip_ids = fields.One2many(
		string='report',
		comodel_name='vit.report_balance_wip',
		inverse_name='report_id'
	)
	data = fields.Binary('File')

	sql = """select 
			pp.id as product_id,
			pt.name,
			pt.default_code,
			(
				select sum(product_uom_qty - qty_delivered)
				from sale_order_line sol 
				join sale_order so on sol.order_id = so.id
				where so.state in ('sale','done')
				and so.date_order < %s
				and sol.product_id = pp.id
			) as total_so_bln_lalu,
			(
				select sum(product_uom_qty - qty_delivered)
				from sale_order_line sol 
				join sale_order so on sol.order_id = so.id
				where so.state in ('sale','done')
				and so.date_order between %s and %s
				and sol.product_id = pp.id
			) as total_so_bln_ini,
			(  
				select sum(quantity)
				from stock_quant sq 
				join stock_location loc on sq.location_id = loc.id
				where 
				sq.product_id = pp.id
				and loc.usage='internal'
			) as onhand,
			(
				select sum(qty_producing) 
				from mrp_workorder wo
				where wo.state = 'progress' and wo.product_id = pp.id and wo.name like 'H%%'
			) as heading,
			(
				select sum(qty_producing) 
				from mrp_workorder wo
				where wo.state = 'progress' and wo.product_id = pp.id and wo.name like 'R%%'
			) as rolling, 
			(
				select sum(qty_producing) 
				from mrp_workorder wo
				where wo.state = 'progress' and wo.product_id = pp.id and wo.name = 'F%%'
			) as furnace, 
			(
				select sum(qty_producing) 
				from mrp_workorder wo
				where wo.state = 'progress' and wo.product_id = pp.id and wo.name like 'P%%'
			) as plating, 
			(
				select sum(qty_producing) 
				from mrp_workorder wo
				where wo.state = 'progress' and wo.product_id = pp.id and wo.name like 'FQ%%'
			) as fq
		from
			product_template pt
			join product_product pp on pp.product_tmpl_id = pt.id 
			join res_company rc on rc.id = pt.company_id
			join product_category pc on pt.categ_id = pc.id where pc.name = 'Finish Good' and rc.id = %s
		"""
	#////////////////////////////////////////////////// GENERATE MASTER \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
	#////////////////////////////////////////////////// GENERATE MASTER \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
	#////////////////////////////////////////////////// GENERATE MASTER \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
	@api.multi
	def generate_master(self):
		if self.name_report == 'Report Balance SO' :
			return self.generate_balance_so()
		else:
			return self.generate_balance_wip()
	
	#////////////////////////////////////////////////// GENERATE EXCEL \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
	@api.multi
	def export_excel(self):
		if self.name_report == 'Report Balance SO' :
			return self.export_excel_so()
		else:
			return self.export_excel_wip()
	
	#////////////////////////////////////////////////// GENERATE SO \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
	@api.multi
	def generate_balance_so(self):

		cr = self.env.cr

		cr.execute(self.sql, (self.date_start, self.date_start, self.date_end, self.company_id.id))
		result = cr.dictfetchall()

		sql = "delete from vit_report_balance_so where report_id=%s"
		cr.execute(sql, (self.id,) )

		for res in result:
			line = self.env['vit.report_balance_so']

			total_so_bln_ini = float(res['total_so_bln_ini']) if res['total_so_bln_ini'] != None else 0
			# if res['total_so_bln_ini'] == None :
			#     total_so_bln_ini = 0
			# else:
			#     total_so_bln_ini = float(res['total_so_bln_ini'])
			total_so_bln_lalu = float(res['total_so_bln_lalu']) if res['total_so_bln_lalu'] != None else 0
			# if res['total_so_bln_lalu'] == None :
			#     total_so_bln_lalu = 0
			# else:
			#     total_so_bln_lalu = float(res['total_so_bln_lalu'])
			onhand = float(res['onhand']) if res['onhand'] != None else 0 
			# if res['onhand'] == None :
			#     onhand = 0
			# else:
			#     onhand = float(res['onhand'])
			heading = float(res['heading']) if res['heading'] != None else 0 
			# if res['heading'] == None :
			#     heading = 0
			# else:
			#     heading = float(res['heading'])
			rolling = float(res['heading']) if res['heading'] != None else 0
			# if res['heading'] == None :
			#     rolling = 0
			# else:
			#     rolling = float(res['heading'])
			furnace = float(res['furnace']) if res['furnace'] != None else 0
			# if res['furnace'] == None :
			#     furnace = 0
			# else:
			#     furnace = float(res['furnace'])
			plating = float(res['plating']) if res['plating'] != None else 0
			# if res['plating'] == None :
			#     plating = 0
			# else:
			#     plating = float(res['plating'])
			fq = float(res['fq']) if res['fq'] != None else 0
			# if res['fq'] == None :
			#     fq = 0
			# else:
			#     fq = float(res['fq'])
				
			wip = onhand + heading + rolling + furnace + plating + fq
			balance = wip - total_so_bln_lalu - total_so_bln_ini

			line.create({
				'report_id': self.id,
				'product_id': res['product_id'],
				'total_so_bln_lalu': total_so_bln_lalu,
				'total_so_bln_ini': total_so_bln_ini,
				'onhand': onhand,
				'heading': heading,
				'rolling': rolling,
				'furnace': furnace,
				'plating': plating,
				'fq': fq,
				'wip_onhand': wip,
				'balance_so': balance ,
			})

	#////////////////////////////////////////////////// GENERATE WIP \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
	@api.multi
	def generate_balance_wip(self):

		cr = self.env.cr

		cr.execute(self.sql, (self.date_start, self.date_start, self.date_end, self.company_id.id))
		result = cr.dictfetchall()

		sql = "delete from vit_report_balance_wip where report_id=%s"
		cr.execute(sql, (self.id,) )

		line = self.env['vit.report_balance_wip']
		for res in result:
		
			onhand = float(res['onhand']) if res['onhand'] != None else 0
			
			heading = float(res['heading']) if res['heading'] != None else 0
		
			rolling = float(res['rolling']) if res['rolling'] != None else 0
	
			furnace = float(res['furnace']) if res['furnace'] != None else 0
		
			plating = float(res['plating']) if res['plating'] != None else 0
			
			fq = float(res['fq']) if res['fq'] != None else 0
				

			line.create({
				'report_id': self.id,
				'product_id': res['product_id'],
				'onhand': onhand,
				'heading': heading,
				'rolling': rolling,
				'furnace': furnace,
				'plating': plating,
				'fq': fq,})
	
	def cell_format(self, workbook):
		cell_format = {}
		cell_format['title'] = workbook.add_format({
			'bold': True,
			'align': 'center',
			'valign': 'vcenter',
			'font_size': 20,
			'font_name': 'Arial',
		})
		cell_format['header'] = workbook.add_format({
			'bold': True,
			'align': 'center',
			'border': True,
			'font_name': 'Arial',
		})
		cell_format['content'] = workbook.add_format({
			'font_size': 11,
			'border': False,
			'font_name': 'Arial',
		})
		cell_format['content_float'] = workbook.add_format({
			'font_size': 11,
			'border': True,
			'num_format': '#,##0.00',
			'font_name': 'Arial',
		})
		cell_format['total'] = workbook.add_format({
			'bold': True,
			'num_format': '#,##0.00',
			'border': True,
			'font_name': 'Arial',
		})
		return cell_format, workbook

	@api.multi
	def export_excel_so(self):
		headers = [
			"No",
			"Product",
			"Code",
			"Total SO Bln. Lalu",
			"Total SO Bln. Ini",
			"On Hand",
			"Heading",
			"Rolling",
			"Furnace",
			"Plating",
			"FQ",
			"WIP + On Hand",
			"Balance SO"
		]

		fp = BytesIO()
		workbook = xlsxwriter.Workbook(fp)
		cell_format, workbook = self.cell_format(workbook)

		if not self.report_so_ids :
			raise Warning("Data tidak ditemukan. Mohon Generate Report terlebih dahulu")

		worksheet = workbook.add_worksheet()
		worksheet.set_column('A:ZZ', 30)
		column_length = len(headers)

		########## parameters
		worksheet.write(0, 4, "REPORT BALANCE SO", cell_format['title'])
		worksheet.write(1, 0, "Tanggal", cell_format['content'])
		worksheet.write(1, 1, self.date_start.strftime("%d-%b-%Y") + ' sampai ' + self.date_end.strftime("%d-%b-%Y"), cell_format['content'])
		worksheet.write(2, 0, "Company", cell_format['content'])
		worksheet.write(2, 1, self.company_id.name , cell_format['content'])

		########### header
		column = 0
		row = 4
		for col in headers:
			worksheet.write(row, column, col, cell_format['header'])
			column += 1

		########### contents
		row = 5
		final_data=[]
		no=1
		for data in self.report_so_ids :
			final_data.append([
				no,
				data.product_id.name,
				data.product_code,
				data.total_so_bln_lalu,
				data.total_so_bln_ini,
				data.onhand,
				data.heading,
				data.rolling,
				data.furnace,
				data.plating,
				data.fq,
				data.wip_onhand,
				data.balance_so,
			])
			no += 1

		for data in final_data:
			column = 0
			for col in data:
				worksheet.write(row, column, col, cell_format['content'] if column<2 else  cell_format['content_float'])
				column += 1
			row += 1

		workbook.close()
		result = base64.encodestring(fp.getvalue())
		filename = self.name_report + '-' + self.company_id.name + '%2Exlsx'
		self.write({'data':result})
		url = "web/content/?model="+self._name+"&id="+str(self.id)+"&field=data&download=true&filename="+filename
		return {
			'type': 'ir.actions.act_url',
			'url': url,
			'target': 'new',
		}

	@api.multi
	def export_excel_wip(self):

		headers = [
			"No",
			"Product",
			"Code",
			"On Hand",
			"Heading",
			"Rolling",
			"Furnace",
			"Plating",
			"FQ",
			"WIP + On Hand",
		]

		fp = BytesIO()
		workbook = xlsxwriter.Workbook(fp)
		cell_format, workbook = self.cell_format(workbook)

		if not self.report_wip_ids :
			raise Warning("Data tidak ditemukan. Mohon Generate Report terlebih dahulu")

		worksheet = workbook.add_worksheet()
		worksheet.set_column('A:ZZ', 30)
		column_length = len(headers)

		########## parameters
		worksheet.write(0, 4, "REPORT BALANCE WIP", cell_format['title'])
		worksheet.write(1, 0, "Tanggal", cell_format['content'])
		worksheet.write(1, 1, self.date_start.strftime("%d-%b-%Y") + ' sampai ' + self.date_end.strftime("%d-%b-%Y"), cell_format['content'])
		worksheet.write(2, 0, "Company", cell_format['content'])
		worksheet.write(2, 1, self.company_id.name , cell_format['content'])

		########### header
		column = 0
		row = 4
		for col in headers:
			worksheet.write(row, column, col, cell_format['header'])
			column += 1

		########### contents
		row = 5
		final_data=[]
		no=1
		for data in self.report_wip_ids :
			final_data.append([
				no,
				data.product_id.name,
				data.product_code,
				data.onhand,
				data.heading,
				data.rolling,
				data.furnace,
				data.plating,
				data.fq,
				data.wip_onhand,
			])
			no += 1

		for data in final_data:
			column = 0
			for col in data:
				worksheet.write(row, column, col, cell_format['content'] if column<2 else  cell_format['content_float'])
				column += 1
			row += 1

		workbook.close()
		result = base64.encodestring(fp.getvalue())
		filename = self.name_report + '-' + self.company_id.name + '%2Exlsx'
		self.write({'data':result})
		url = "web/content/?model="+self._name+"&id="+str(self.id)+"&field=data&download=true&filename="+filename
		return {
			'type': 'ir.actions.act_url',
			'url': url,
			'target': 'new',
		}

class report_balance_so(models.Model):
	_name = 'vit.report_balance_so'

	report_id = fields.Many2one(comodel_name='vit.report_balance', string="Report")
	product_id = fields.Many2one(comodel_name='product.product', string="Product Name")
	product_code = fields.Char(string='Product Code', related='product_id.default_code')
	total_so_bln_lalu = fields.Float(string='Total SO Bulan Lalu')
	total_so_bln_ini = fields.Float(string='Total SO Bulan Ini')
	onhand = fields.Float(string='On hand')
	heading = fields.Float(string='Heading')
	rolling = fields.Float(string='Rolling')
	furnace = fields.Float(string='Furnace')
	plating = fields.Float(string='Plating')
	fq = fields.Float(string='FQ')
	wip_onhand = fields.Float(string='Wip Onhand')
	balance_so = fields.Float(string='Balance SO')

class report_balance_wip(models.Model):
	_name = "vit.report_balance_wip"
	
	product_code = fields.Char( string="Product code", related='product_id.default_code',)
	onhand = fields.Float( string="On hand", )
	heading = fields.Float( string="Heading", )
	rolling = fields.Float( string="Rolling", )
	furnace = fields.Float( string="Furnace", )
	plating = fields.Float( string="Plating", )
	fq = fields.Float( string="FQ", )
	wip_onhand = fields.Float( string="WIP", )
	


	report_id = fields.Many2one(comodel_name="vit.report_balance",  string="Report",)
	product_id = fields.Many2one(comodel_name="product.product",  string="Product Name",)